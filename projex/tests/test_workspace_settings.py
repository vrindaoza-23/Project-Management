# Copyright (c) 2026, Projex and Contributors
# See license.txt

"""Integration tests for workspace settings endpoints and their permission gating.

Covers the access model the SPA relies on:
  - workspace admins (or privileged users) can read/manage; plain members cannot
  - the last admin of a workspace cannot be removed or demoted (no orphaning)
  - reads are gated to members + privileged users
  - bootstrap.is_member scopes the settings workspace switcher

The workspace API commits internally (frappe.db.commit), so the framework's
automatic rollback can't undo it — tearDown deletes every fixture explicitly
(and runs even when a test fails), leaving the site exactly as it found it.
"""

import json

import frappe
from frappe.tests import IntegrationTestCase

from projex import api


def _make_user(email):
    if not frappe.db.exists("User", email):
        u = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": email.split("@")[0],
            "send_welcome_email": 0, "user_type": "System User",
        })
        u.append("roles", {"role": "Projex Member"})
        u.insert(ignore_permissions=True)
    return email


class TestWorkspaceSettings(IntegrationTestCase):
    def setUp(self):
        # OWNER creates the workspace, so OWNER is its sole Admin member.
        self.owner = _make_user("wss_owner@projex.test")
        self.member = _make_user("wss_member@projex.test")
        self.outsider = _make_user("wss_outsider@projex.test")
        frappe.set_user(self.owner)
        self.ws = api.create_workspace("WSS Test Workspace")["name"]
        frappe.set_user("Administrator")

    def tearDown(self):
        # API methods commit, so undo every fixture by hand (runs on failure too).
        frappe.set_user("Administrator")
        for pj in frappe.get_all("Projex Project", filters={"workspace": self.ws}, pluck="name"):
            frappe.delete_doc("Projex Project", pj, ignore_permissions=True, force=True)
        if frappe.db.exists("Projex Project", "WSS"):
            frappe.delete_doc("Projex Project", "WSS", ignore_permissions=True, force=True)
        for tm in frappe.get_all("Projex Team", filters={"workspace": self.ws}, pluck="name"):
            frappe.delete_doc("Projex Team", tm, ignore_permissions=True, force=True)
        if frappe.db.exists("Projex Workspace", self.ws):
            frappe.delete_doc("Projex Workspace", self.ws, ignore_permissions=True, force=True)
        for email in (self.owner, self.member, self.outsider):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, ignore_permissions=True, force=True)
        frappe.db.commit()

    # --- reads ---------------------------------------------------------------
    def test_member_can_read_detail(self):
        api.add_member("Projex Workspace", self.ws, self.member, "Member")
        frappe.set_user(self.member)
        detail = api.get_workspace_detail(self.ws)
        self.assertTrue(any(m["user"] == self.member for m in detail["members"]))
        self.assertFalse(detail["workspace"]["can_manage"])  # a plain member can't manage

    def test_non_member_cannot_read_detail(self):
        frappe.set_user(self.outsider)
        self.assertRaises(frappe.PermissionError, lambda: api.get_workspace_detail(self.ws))

    def test_privileged_can_read_any_workspace(self):
        frappe.set_user("Administrator")  # System Manager
        self.assertTrue(api.get_workspace_detail(self.ws)["workspace"]["can_manage"])

    # --- writes are gated ----------------------------------------------------
    def test_owner_can_manage(self):
        frappe.set_user(self.owner)
        api.add_member("Projex Workspace", self.ws, self.member, "Member")
        detail = api.get_workspace_detail(self.ws)
        self.assertTrue(any(m["user"] == self.member for m in detail["members"]))
        self.assertTrue(detail["workspace"]["can_manage"])

    def test_plain_member_cannot_manage(self):
        api.add_member("Projex Workspace", self.ws, self.member, "Member")
        frappe.set_user(self.member)
        self.assertRaises(frappe.PermissionError,
                          lambda: api.add_member("Projex Workspace", self.ws, self.outsider, "Member"))
        self.assertRaises(frappe.PermissionError,
                          lambda: api.remove_member("Projex Workspace", self.ws, self.owner))
        self.assertRaises(frappe.PermissionError,
                          lambda: api.update_member_role("Projex Workspace", self.ws, self.owner, "Guest"))
        self.assertRaises(frappe.PermissionError,
                          lambda: api.create_team(self.ws, "Nope"))
        self.assertRaises(frappe.PermissionError,
                          lambda: api.update_workspace(self.ws, json.dumps({"description": "x"})))
        self.assertRaises(frappe.PermissionError,
                          lambda: api.delete_workspace(self.ws))

    def test_promoted_member_can_manage(self):
        api.add_member("Projex Workspace", self.ws, self.member, "Admin")
        frappe.set_user(self.member)
        # An Admin member may now create (and clean up) a team without error.
        team = api.create_team(self.ws, "Promoted Team")["name"]
        api.delete_team(team)
        self.assertFalse(frappe.db.exists("Projex Team", team))

    # --- admin lockout guard -------------------------------------------------
    def test_cannot_remove_sole_admin(self):
        frappe.set_user(self.owner)
        with self.assertRaises(frappe.ValidationError):
            api.remove_member("Projex Workspace", self.ws, self.owner)
        # still a member after the refused removal
        self.assertTrue(frappe.db.exists("Projex Workspace Member",
                                         {"parent": self.ws, "user": self.owner}))

    def test_cannot_demote_sole_admin(self):
        frappe.set_user(self.owner)
        with self.assertRaises(frappe.ValidationError):
            api.update_member_role("Projex Workspace", self.ws, self.owner, "Member")

    def test_can_remove_admin_when_another_exists(self):
        api.add_member("Projex Workspace", self.ws, self.member, "Admin")
        frappe.set_user(self.owner)
        api.remove_member("Projex Workspace", self.ws, self.owner)  # should not raise
        self.assertFalse(frappe.db.exists("Projex Workspace Member",
                                          {"parent": self.ws, "user": self.owner}))

    # --- delete guard --------------------------------------------------------
    def test_delete_refuses_while_projects_exist(self):
        frappe.set_user(self.owner)
        api.create_project(json.dumps({
            "project_name": "WSS Project", "key": "WSS", "workspace": self.ws,
        }))
        with self.assertRaises(frappe.ValidationError):
            api.delete_workspace(self.ws)
        self.assertTrue(frappe.db.exists("Projex Workspace", self.ws))

    def test_delete_succeeds_when_empty(self):
        frappe.set_user(self.owner)
        api.delete_workspace(self.ws)
        self.assertFalse(frappe.db.exists("Projex Workspace", self.ws))

    # --- bootstrap scoping ---------------------------------------------------
    def test_bootstrap_is_member_flag(self):
        frappe.set_user(self.owner)
        wmap = {w["name"]: w.get("is_member") for w in api.bootstrap()["workspaces"]}
        self.assertIs(wmap.get(self.ws), True)

        frappe.set_user(self.outsider)
        wmap = {w["name"]: w.get("is_member") for w in api.bootstrap()["workspaces"]}
        self.assertIs(wmap.get(self.ws), False)

        frappe.set_user("Administrator")  # privileged sees every workspace as accessible
        self.assertTrue(all(w.get("is_member") is True for w in api.bootstrap()["workspaces"]))
