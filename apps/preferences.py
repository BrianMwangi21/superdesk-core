# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk

from flask import request
from eve.utils import config
from superdesk.preferences import get_user_notification_preferences
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk import get_backend
from superdesk import get_resource_service
from superdesk.workflow import get_privileged_actions
from superdesk.validation import ValidationError
from flask_babel import _, lazy_gettext


_preferences_key = "preferences"
_user_preferences_key = "user_preferences"
_session_preferences_key = "session_preferences"
_privileges_key = "active_privileges"
_action_key = "allowed_actions"
logger = logging.getLogger(__name__)


def init_app(app) -> None:
    endpoint_name = "preferences"
    service = PreferencesService(endpoint_name, backend=get_backend())
    PreferencesResource(endpoint_name, app=app, service=service)
    app.on_session_end -= service.on_session_end
    app.on_session_end += service.on_session_end
    app.on_role_privileges_updated -= service.on_role_privileges_updated
    app.on_role_privileges_updated += service.on_role_privileges_updated
    superdesk.intrinsic_privilege(resource_name=endpoint_name, method=["PATCH"])


def available_user_preferences():
    available = {}
    for key, pref in superdesk.default_user_preferences.items():
        available[key] = dict()
        available[key].update(pref.value)
        for field in ("label", "category"):
            if getattr(pref, field, None):
                available[key][field] = str(getattr(pref, field))
    return available


def enhance_document_with_default_prefs(doc):
    user_prefs = doc.get(_user_preferences_key, {})
    available = available_user_preferences()
    available.update(user_prefs)

    def sync_field(field, dest, value=None):
        if not isinstance(dest, dict):
            return
        if value:
            dest[field] = str(value)
        elif dest.get(field):
            dest.pop(field, None)

    # make sure label and category are up-to-date
    for k, v in available.items():
        default = superdesk.default_user_preferences.get(k)
        if default:
            sync_field("label", v, default.label)
            sync_field("category", v, default.category)

    doc[_user_preferences_key] = available


class PreferencesResource(Resource):
    datasource = {
        "source": "users",
        "projection": {
            _session_preferences_key: 1,
            _user_preferences_key: 1,
            _privileges_key: 1,
            _action_key: 1,
            "_etag": 1,
            "role": 1,
            "user_type": 1,
            "privileges": 1,
        },
    }
    schema = {
        _session_preferences_key: {"type": "dict", "required": True, "allow_unknown": True},
        _user_preferences_key: {"type": "dict", "required": True, "allow_unknown": True},
        _privileges_key: {"type": "dict", "allow_unknown": True},
        _action_key: {"type": "list"},
        # we need these to get user/role info
        "role": {"type": "string"},
        "user_type": {"type": "string"},
        "privileges": {"type": "dict"},
    }
    allow_unknown = True
    resource_methods = []
    item_methods = ["GET", "PATCH"]
    merge_nested_documents = True

    superdesk.register_default_user_preference(
        "feature:preview",
        {
            "type": "bool",
            "enabled": False,
            "default": False,
            "privileges": ["feature_preview"],
        },
        label=lazy_gettext("Enable Feature Preview"),
        category=lazy_gettext("feature"),
    )

    superdesk.register_default_user_preference(
        "archive:view",
        {
            "type": "string",
            "allowed": ["mgrid", "compact"],
            "view": "mgrid",
            "default": "mgrid",
        },
        label=lazy_gettext("Users archive view format"),
        category=lazy_gettext("archive"),
    )

    superdesk.register_default_user_preference(
        "application:theme",
        {
            "type": "string",
            "allowed": ["light-ui", "dark-ui"],
            "theme": "light-ui",
        },
    )

    superdesk.register_default_user_preference(
        "singleline:view",
        {
            "type": "bool",
            "enabled": None,
            "default": False,
        },
        label=lazy_gettext("Enable Single Line View"),
        category=lazy_gettext("rows"),
    )

    superdesk.register_default_user_preference(
        "editor:theme",
        {
            "type": "string",
            "theme": "",
        },
    )

    superdesk.register_default_user_preference("workqueue:items", {"items": []})

    superdesk.register_default_user_preference("dashboard:ingest", {"providers": []})

    superdesk.register_default_user_preference(
        "agg:view",
        {
            "active": {},
        },
    )

    superdesk.register_default_user_preference("templates:recent", {})

    superdesk.register_default_user_preference(
        "dateline:located",
        {
            "type": "dict",
        },
        label=lazy_gettext("Located"),
        category=lazy_gettext("article_defaults"),
    )

    superdesk.register_default_user_preference(
        "categories:preferred",
        {
            "type": "dict",
            "selected": {},
        },
        label=lazy_gettext("Preferred Categories"),
        category=lazy_gettext("categories"),
    )

    superdesk.register_default_user_preference(
        "desks:preferred",
        {
            "type": "dict",
            "selected": {},
        },
        label=lazy_gettext("Preferred Desks"),
        category=lazy_gettext("desks"),
    )

    superdesk.register_default_user_preference(
        "article:default:place",
        {"type": "list", "place": []},
        label=lazy_gettext("Place"),
        category=lazy_gettext("article_defaults"),
    )

    superdesk.register_default_user_preference(
        "spellchecker:status", {"type": "bool", "enabled": True, "default": True}
    )

    superdesk.register_default_user_preference(
        "contacts:view",
        {
            "type": "string",
            "allowed": ["mgrid", "compact"],
            "view": "mgrid",
            "default": "mgrid",
        },
        label=lazy_gettext("Users contacts view format"),
        category=lazy_gettext("contacts"),
    )

    superdesk.register_default_user_preference("destination:active", {})

    superdesk.register_default_user_preference("extensions", {})

    superdesk.register_default_user_preference(
        "search:filters_panel_open", {"type": "bool", "enabled": True, "default": True}
    )

    superdesk.register_default_user_preference("masterdesk:desks", {})

    superdesk.register_default_user_preference("editor:char_limit_ui", {})
    superdesk.register_default_user_preference("editor:pinned_widget", {})

    superdesk.register_default_session_preference("scratchpad:items", [])
    superdesk.register_default_session_preference("desk:last_worked", "")
    superdesk.register_default_session_preference("desk:items", [])
    superdesk.register_default_session_preference("stage:items", [])
    superdesk.register_default_session_preference("pinned:items", [])

    # @deprecated, keep to avoid validation error
    superdesk.register_default_user_preference("mark_for_user:notification", {})
    superdesk.register_default_user_preference("assignment:notification", {})


class PreferencesService(BaseService):
    def on_session_end(self, user_id, session_id, is_last_session):
        service = get_resource_service("users")
        user_doc = service.find_one(req=None, _id=user_id)

        if is_last_session:
            service.system_update(user_id, {_session_preferences_key: {}}, user_doc)

        session_prefs = user_doc.get(_session_preferences_key, {}).copy()

        if not isinstance(session_id, str):
            session_id = str(session_id)

        if session_id in session_prefs:
            del session_prefs[session_id]
            service.system_update(user_id, {_session_preferences_key: session_prefs}, user_doc)

    def set_session_based_prefs(self, session_id, user_id):
        service = get_resource_service("users")
        user_doc = service.find_one(req=None, _id=user_id)

        session_prefs = user_doc.get(_session_preferences_key, {})
        available = dict(superdesk.default_session_preferences)
        if available.get("desk:last_worked") == "" and user_doc.get("desk"):
            available["desk:last_worked"] = user_doc.get("desk")

        session_prefs.setdefault(str(session_id), available)
        service.system_update(user_id, {_session_preferences_key: session_prefs}, user_doc)

    def set_user_initial_prefs(self, user_doc):
        if _user_preferences_key not in user_doc:
            orig_user_prefs = user_doc.get(_preferences_key, {})
            available = available_user_preferences()
            available.update(orig_user_prefs)
            user_doc[_user_preferences_key] = available

    def find_one(self, req, **lookup):
        session = get_resource_service("sessions").find_one(req=None, _id=lookup["_id"])
        _id = session["user"] if session else lookup["_id"]
        doc = get_resource_service("users").find_one(req, _id=_id)
        if doc:
            doc["_id"] = session["_id"] if session else _id
        return doc

    def on_fetched_item(self, doc):
        session_id = request.view_args["_id"]
        session_prefs = doc.get(_session_preferences_key, {}).get(session_id, {})
        doc[_session_preferences_key] = session_prefs
        self.enhance_document_with_user_privileges(doc)
        enhance_document_with_default_prefs(doc)
        self._filter_preferences_by_privileges(doc)

    def on_update(self, updates, original):
        existing_user_preferences = original.get(_user_preferences_key, {}).copy()
        existing_session_preferences = original.get(_session_preferences_key, {}).copy()

        self.update_user_prefs(updates, existing_user_preferences)
        session_id = request.view_args["_id"]
        self.update_session_prefs(updates, existing_session_preferences, session_id)

    def update_session_prefs(self, updates, existing_session_preferences, session_id):
        session_prefs = updates.get(_session_preferences_key)
        if session_prefs is not None:
            for k in (k for k, v in session_prefs.items() if k not in superdesk.default_session_preferences):
                raise ValidationError(_("Invalid preference: {preference}").format(preference=k))

            existing = existing_session_preferences.get(session_id, {})
            existing.update(session_prefs)
            existing_session_preferences[session_id] = existing
            updates[_session_preferences_key] = existing_session_preferences

    def update_user_prefs(self, updates, existing_user_preferences):
        user_prefs = updates.get(_user_preferences_key)
        if user_prefs is not None:
            # check if the input is validated against the default values
            for k in (k for k in user_prefs if k not in superdesk.default_user_preferences):
                raise ValidationError(_("Invalid preference: {preference}").format(preference=k))

            existing_user_preferences.update(user_prefs)
            updates[_user_preferences_key] = existing_user_preferences

    def update(self, id, updates, original):
        session = get_resource_service("sessions").find_one(req=None, _id=original["_id"])
        original_unpatched = self.backend.find_one(self.datasource, req=None, _id=session["user"])
        updated = original_unpatched.copy()
        updated.update(updates)
        del updated["_id"]
        res = self.backend.update(self.datasource, original_unpatched["_id"], updated, original_unpatched)
        updates.update(updated)
        # Return only the patched session prefs
        session_prefs = updates.get(_session_preferences_key, {}).get(str(original["_id"]), {})
        updates[_session_preferences_key] = session_prefs
        self.enhance_document_with_user_privileges(updates)
        enhance_document_with_default_prefs(updates)
        return res

    def enhance_document_with_user_privileges(self, user_doc):
        role_doc = get_resource_service("users").get_role(user_doc)
        get_resource_service("users").set_privileges(user_doc, role_doc)
        user_doc[_action_key] = get_privileged_actions(user_doc[_privileges_key])

    def get_user_preference(self, user_id):
        """
        This function returns preferences for the user.
        """
        doc = get_resource_service("users").find_one(req=None, _id=user_id)
        if doc is None:
            return {}
        prefs = doc.get(_user_preferences_key, {})
        return prefs

    def email_notification_is_enabled(self, user_id=None) -> bool:
        """
        This function checks if email notification is enabled or not based on the preferences.
        """
        if user_id:
            user = get_resource_service("users").find_one(req=None, _id=user_id)
            if not user:
                return False
            return get_user_notification_preferences(user)["email"]
        return False

    def is_authorized(self, **kwargs):
        """
        Returns False if logged-in user is trying to update other user's or session's privileges.

        :param kwargs:
        :return: True if authorized, False otherwise
        """
        if not kwargs.get("_id") or not kwargs.get("user_id"):
            return False

        session = get_resource_service("sessions").find_one(req=None, _id=kwargs.get("_id"))
        if not session:
            return False

        return str(kwargs.get("user_id")) == str(session.get("user"))

    def on_role_privileges_updated(self, role, role_users):
        """Runs when user privilage has been updated.

        Update the session for active user so that preferences can be reloaded.

        :param dict role: role getting updated
        :param list role_users: list of user belonging to the role.
        """
        if not role_users or not role:
            return

        logger.info("On_Role_Privileges_Updated: Updating Users for Role:{}.".format(role.get(config.ID_FIELD)))
        for user in role_users:
            try:
                super().update(user[config.ID_FIELD], {}, user)
            except Exception:
                logger.warn(
                    "On_Role_Privileges_Updated:Failed to update user:{} with role:{}.".format(
                        user.get(config.ID_FIELD), role.get(config.ID_FIELD)
                    ),
                    exc_info=True,
                )

    def _filter_preferences_by_privileges(self, doc):
        privileges = doc[_privileges_key]
        preferences = doc[_user_preferences_key]

        def has_missing_privileges(prefs):
            prefs = prefs if isinstance(prefs, list) else [prefs]
            return [priv for pref in prefs for priv in pref.get("privileges", []) if not privileges.get(priv)]

        doc[_user_preferences_key] = {k: v for k, v in preferences.items() if not has_missing_privileges(v)}
