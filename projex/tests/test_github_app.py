# Copyright (c) 2026, Projex and Contributors
# See license.txt

"""Tests for the GitHub App connection flow: manifest, credential conversion,
RS256 JWT minting, installation-token caching, and token routing.

External GitHub calls are mocked; the crypto (RS256 sign/verify) is exercised
for real against a throwaway RSA key so a broken signature would fail here.
"""

from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import frappe
from frappe.tests import IntegrationTestCase

from projex import github, github_app

APP_FIELDS = ("app_id", "app_slug", "installation_id", "client_id", "client_secret", "private_key")


def _rsa_pem():
	key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
	private = key.private_bytes(
		serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
	).decode()
	public = key.public_key().public_bytes(
		serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
	).decode()
	return private, public


class TestGithubApp(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self._reset()

	def tearDown(self):
		self._reset()

	def _reset(self):
		s = frappe.get_doc("Projex GitHub Settings")
		for f in APP_FIELDS:
			setattr(s, f, "")
		s.enabled = 0
		s.save(ignore_permissions=True)
		frappe.cache().delete_value(github_app.TOKEN_CACHE)
		frappe.db.commit()

	# -- manifest ------------------------------------------------------------ #
	def test_manifest_shape(self):
		out = github_app.app_manifest()
		self.assertIn("github.com/settings/apps/new", out["post_url"])
		manifest = frappe.parse_json(out["manifest"])
		self.assertIn("/api/method/projex.github.webhook", manifest["hook_attributes"]["url"])
		self.assertIn("/api/method/projex.github_app.app_created", manifest["redirect_url"])
		self.assertEqual(manifest["default_permissions"]["issues"], "write")
		self.assertIn("pull_request", manifest["default_events"])

	def test_state_is_one_time(self):
		state = github_app.app_manifest()["state"]
		self.assertTrue(github_app._valid_state(state))
		self.assertFalse(github_app._valid_state(state))  # consumed

	# -- credential conversion ----------------------------------------------- #
	def test_store_app_persists_credentials(self):
		private, _ = _rsa_pem()
		github_app._store_app({
			"id": 424242, "slug": "projex-acme", "client_id": "Iv1.abc",
			"client_secret": "secret123", "pem": private, "webhook_secret": "whsec",
		})
		s = frappe.get_doc("Projex GitHub Settings")
		self.assertEqual(s.app_id, "424242")
		self.assertEqual(s.app_slug, "projex-acme")
		self.assertTrue(s.enabled)
		self.assertEqual(s.get_password("private_key"), private)
		self.assertEqual(s.get_password("webhook_secret"), "whsec")

	# -- JWT + installation token -------------------------------------------- #
	def test_app_jwt_is_valid_rs256(self):
		private, public = _rsa_pem()
		s = frappe.get_doc("Projex GitHub Settings")
		s.app_id = "555"
		s.private_key = private
		s.save(ignore_permissions=True)

		token = github_app._app_jwt(frappe.get_doc("Projex GitHub Settings"))
		self.assertIsNotNone(token)
		decoded = jwt.decode(token, public, algorithms=["RS256"])
		self.assertEqual(decoded["iss"], "555")
		self.assertLess(decoded["exp"] - decoded["iat"], 601)  # <= 10 min window

	def test_installation_token_caches(self):
		private, _ = _rsa_pem()
		s = frappe.get_doc("Projex GitHub Settings")
		s.app_id = "555"
		s.installation_id = "999"
		s.private_key = private
		s.save(ignore_permissions=True)

		resp = {"token": "ghs_installtoken", "expires_at": "2099-01-01T00:00:00Z"}
		with patch.object(github_app, "_gh_request", return_value=resp) as req:
			first = github_app.installation_token()
			second = github_app.installation_token()  # served from cache
		self.assertEqual(first, "ghs_installtoken")
		self.assertEqual(second, "ghs_installtoken")
		req.assert_called_once()  # token minted once, then cached

	def test_installation_token_none_when_not_configured(self):
		self.assertFalse(github_app.is_app_configured())
		self.assertIsNone(github_app.installation_token())

	# -- token routing ------------------------------------------------------- #
	def test_access_token_prefers_installation(self):
		with patch.object(github_app, "installation_token", return_value="inst_tok"):
			self.assertEqual(github._access_token(), "inst_tok")

	def test_access_token_falls_back_to_pat(self):
		s = frappe.get_doc("Projex GitHub Settings")
		s.access_token = "ghp_manual"
		s.save(ignore_permissions=True)
		with patch.object(github_app, "installation_token", return_value=None):
			self.assertEqual(github._access_token(), "ghp_manual")

	def test_disconnect_app_clears_everything(self):
		private, _ = _rsa_pem()
		github_app._store_app({"id": 1, "slug": "x", "pem": private, "webhook_secret": "w"})
		github_app.disconnect_app()
		s = frappe.get_doc("Projex GitHub Settings")
		self.assertFalse(s.app_id)
		self.assertFalse(s.installation_id)
		self.assertFalse(s.enabled)
