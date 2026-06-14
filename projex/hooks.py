app_name = "projex"
app_title = "Projex"
app_publisher = "Projex"
app_description = "Linear-grade project management for Frappe"
app_email = "vrindaoza23@gmail.com"
app_license = "agpl-3.0"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "projex",
# 		"logo": "/assets/projex/logo.png",
# 		"title": "Projex",
# 		"route": "/projex",
# 		"has_permission": "projex.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/projex/css/projex.css"
# app_include_js = "/assets/projex/js/projex.js"

# include js, css files in header of web template
# web_include_css = "/assets/projex/css/projex.css"
# web_include_js = "/assets/projex/js/projex.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "projex/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "projex/public/icons.svg"

# Home Pages
# ----------

# Serve the Vue SPA: deep links under /projex resolve to the built page.
website_route_rules = [
	{"from_route": "/projex/<path:app_path>", "to_route": "projex"},
]

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "projex.utils.jinja_methods",
# 	"filters": "projex.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "projex.install.before_install"
after_install = [
	"projex.setup.defaults.run",
	"projex.setup.erpnext_integration.setup_custom_fields",
]

# Seed defaults (roles + global statuses) and re-apply optional ERPNext custom
# fields after every migrate. Both are idempotent.
after_migrate = [
	"projex.setup.defaults.run",
	"projex.setup.erpnext_integration.setup_custom_fields",
]

# Uninstallation
# ------------

# before_uninstall = "projex.uninstall.before_uninstall"
# after_uninstall = "projex.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "projex.utils.before_app_install"
# after_app_install = "projex.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "projex.utils.before_app_uninstall"
# after_app_uninstall = "projex.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "projex.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "projex.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Projex Project": "projex.projex.doctype.projex_project.projex_project.get_permission_query_conditions",
	"Projex Issue": "projex.projex.doctype.projex_issue.projex_issue.get_permission_query_conditions",
	"Projex Comment": "projex.projex.doctype.projex_comment.projex_comment.get_permission_query_conditions",
}

has_permission = {
	"Projex Project": "projex.projex.doctype.projex_project.projex_project.has_permission",
	"Projex Issue": "projex.projex.doctype.projex_issue.projex_issue.has_permission",
}

# Validate file attachments on Projex issues (size + blocked extensions).
doc_events = {
	"File": {"before_insert": "projex.api.validate_attachment"},
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"projex.tasks.all"
# 	],
# 	"daily": [
# 		"projex.tasks.daily"
# 	],
# 	"hourly": [
# 		"projex.tasks.hourly"
# 	],
# 	"weekly": [
# 		"projex.tasks.weekly"
# 	],
# 	"monthly": [
# 		"projex.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "projex.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "projex.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "projex.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "projex.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["projex.utils.before_request"]
# after_request = ["projex.utils.after_request"]

# Job Events
# ----------
# before_job = ["projex.utils.before_job"]
# after_job = ["projex.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"projex.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

