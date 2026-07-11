# Copyright (c) 2026, Projex and Contributors
# See license.txt

"""Tests for the GitHub integration: signature, magic-word parsing, linking and
the auto status transitions (PR open -> In Progress, merge -> Done).

Handlers are exercised directly with simulated GitHub payloads (the HTTP layer
only adds signature verification, covered separately). The Single settings doc
is mutated in setUp and reset in tearDown so the site is left as found.
"""

import hashlib
import hmac
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from projex import github

PROJECT = "BIL"
REPO = "acme/web"
SECRET = "unit-test-secret"


class TestGithub(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.created = []
		s = frappe.get_doc("Projex GitHub Settings")
		s.enabled = 1
		s.webhook_secret = SECRET
		s.access_token = ""  # keep outbound calls (and enqueue) out of the tests
		s.move_on_open = 1
		s.move_on_merge = 1
		s.close_on_keyword = 1
		s.post_comment = 1
		s.repos = []
		s.append("repos", {"repository": REPO, "project": PROJECT})
		s.save(ignore_permissions=True)
		frappe.db.commit()
		self.settings = frappe.get_doc("Projex GitHub Settings")

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in self.created:
			frappe.db.delete("Projex GitHub Link", {"issue": name})
			frappe.db.delete("Projex Comment", {"issue": name})
			frappe.db.delete("Projex Activity", {"issue": name})
			frappe.db.delete("Projex Notification", {"issue": name})
			if frappe.db.exists("Projex Issue", name):
				frappe.delete_doc("Projex Issue", name, force=True, ignore_permissions=True)
		s = frappe.get_doc("Projex GitHub Settings")
		s.enabled = 0
		s.webhook_secret = ""
		s.repos = []
		s.save(ignore_permissions=True)
		frappe.db.commit()

	# -- helpers ------------------------------------------------------------- #
	def _make_issue(self, title="ZZ github test"):
		issue = frappe.get_doc({"doctype": "Projex Issue", "project": PROJECT, "title": title}).insert(
			ignore_permissions=True
		)
		self.created.append(issue.name)
		return issue.name

	def _cat(self, issue):
		st = frappe.db.get_value("Projex Issue", issue, "status")
		return frappe.db.get_value("Projex Status", st, "category")

	def _pr(self, key, **over):
		# Neutral title on purpose — "Fix/Closes <key>" is a GitHub closing
		# keyword, so tests opt into that explicitly via body.
		pr = {
			"number": 101, "title": f"Work on {key}", "body": "", "html_url": f"https://github.com/{REPO}/pull/101",
			"state": "open", "draft": False, "merged": False,
			"user": {"login": "octocat", "avatar_url": "https://x/y.png"},
			"head": {"ref": f"octocat/{key.lower()}"},
		}
		pr.update(over)
		return pr

	def _event(self, action, pr):
		github.handle_pull_request(
			{"action": action, "repository": {"full_name": REPO}, "pull_request": pr}, self.settings
		)

	# -- tests --------------------------------------------------------------- #
	def test_signature_verification(self):
		raw = b'{"hello":"world"}'
		good = "sha256=" + hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
		self.assertTrue(github._verify_signature(raw, good, SECRET))
		self.assertFalse(github._verify_signature(raw, "sha256=deadbeef", SECRET))
		self.assertFalse(github._verify_signature(raw, good, "wrong-secret"))
		self.assertFalse(github._verify_signature(raw, "", SECRET))

	def test_parsing_is_scoped_to_project(self):
		key = self._make_issue()
		found = github._issues_in(f"work on {key} and ZZZ-9999", PROJECT)
		self.assertEqual(found, [key])  # in-project key kept, unknown key dropped

	def test_pr_open_links_and_starts(self):
		key = self._make_issue()
		self.assertEqual(self._cat(key), "unstarted")
		self._event("opened", self._pr(key))

		links = github._links(key)
		self.assertEqual(len(links), 1)
		self.assertEqual(links[0]["state"], "open")
		self.assertEqual(links[0]["number"], 101)
		self.assertEqual(self._cat(key), "started")
		self.assertEqual(frappe.db.count("Projex Comment", {"issue": key}), 1)

	def test_pr_merge_completes_with_keyword(self):
		key = self._make_issue()
		self._event("opened", self._pr(key))
		self._event("closed", self._pr(key, merged=True, state="closed", body=f"closes {key}"))

		self.assertEqual(self._cat(key), "completed")
		link = github._links(key)[0]
		self.assertEqual(link["state"], "merged")
		self.assertTrue(link["merged"])

	def test_merge_without_keyword_does_not_complete(self):
		key = self._make_issue()
		self._event("opened", self._pr(key))
		# merged, but body has no closing keyword and close_on_keyword is on
		self._event("closed", self._pr(key, merged=True, state="closed", body="just merging"))

		self.assertEqual(self._cat(key), "started")  # stays In Progress
		self.assertEqual(github._links(key)[0]["state"], "merged")  # link still reflects merge

	def test_unmapped_repo_is_ignored(self):
		key = self._make_issue()
		github.handle_pull_request(
			{"action": "opened", "repository": {"full_name": "someone/else"}, "pull_request": self._pr(key)},
			self.settings,
		)
		self.assertEqual(github._links(key), [])
		self.assertEqual(self._cat(key), "unstarted")

	# -- outbound (mocked GitHub REST) --------------------------------------- #
	def test_push_pr_comment_targets_the_pr(self):
		key = self._make_issue()
		with patch.object(github, "_access_token", return_value="tok"), patch.object(github, "_gh_request") as req:
			github.push_pr_comment(REPO, 55, [key])
		req.assert_called_once()
		args, kwargs = req.call_args
		self.assertEqual(args[0], "POST")
		self.assertEqual(args[1], f"/repos/{REPO}/issues/55/comments")
		self.assertIn(key, kwargs["json"]["body"])

	def test_push_pr_comment_noop_without_token(self):
		with patch.object(github, "_access_token", return_value=None), patch.object(github, "_gh_request") as req:
			github.push_pr_comment(REPO, 55, ["BIL-1"])
		req.assert_not_called()

	def test_refresh_reconciles_state_and_ci(self):
		key = self._make_issue()
		link = frappe.get_doc({
			"doctype": "Projex GitHub Link", "issue": key, "kind": "Pull Request",
			"repository": REPO, "number": 55, "state": "draft",
		}).insert(ignore_permissions=True)

		def fake(method, path, token, json=None):
			if path.endswith("/pulls/55"):
				return {"merged": False, "draft": False, "state": "open", "head": {"sha": "abc"}}
			if "/commits/abc/status" in path:
				return {"state": "success"}
			return {}

		with patch.object(github, "_gh_request", side_effect=fake):
			github._refresh_one(frappe._dict({"name": link.name, "repository": REPO, "number": 55}), "tok")

		row = frappe.db.get_value("Projex GitHub Link", link.name, ["state", "ci_status"], as_dict=True)
		self.assertEqual(row.state, "open")
		self.assertEqual(row.ci_status, "success")

	def test_remove_link(self):
		key = self._make_issue()
		link = frappe.get_doc({
			"doctype": "Projex GitHub Link", "issue": key, "kind": "Pull Request",
			"repository": REPO, "number": 55,
		}).insert(ignore_permissions=True)
		github.remove_link(link.name)
		self.assertFalse(frappe.db.exists("Projex GitHub Link", link.name))

	def test_refresh_links_requires_token(self):
		key = self._make_issue()
		with patch.object(github, "_access_token", return_value=None):
			self.assertRaises(frappe.ValidationError, github.refresh_links, key)
