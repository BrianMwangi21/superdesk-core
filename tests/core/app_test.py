from unittest import TestCase, mock

from superdesk.core.app import SuperdeskAsyncApp
from superdesk.core.privileges import Privilege
from superdesk.tests import MockWSGI


class SuperdeskAsyncAppTestCase(TestCase):
    def test_construction(self):
        # Test starting the app, and the ``running`` property
        app = SuperdeskAsyncApp(MockWSGI(config={}))
        self.assertFalse(app.running)
        app.start()
        self.assertTrue(app.running)

        # Test exception raised if attempting to start an already running app
        with self.assertRaises(RuntimeError):
            app.start()

    def test_loading_modules(self):
        # Test module loading, and populating of the path attribute
        config = {"MODULES": ["tests.core.modules.a", "tests.core.modules.b"]}
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        self.assertEqual(len(app._imported_modules), 2)
        self.assertEqual(app._imported_modules["tests.module_a"].path, "tests.core.modules.a")
        self.assertEqual(app._imported_modules["tests.module_b"].path, "tests.core.modules.b")

        # Test overriding a module
        config["MODULES"] = ["tests.core.modules.a", "tests.core.modules.a2"]
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        self.assertEqual(app._imported_modules["tests.module_a"].path, "tests.core.modules.a2")

        # Test frozen modules cannot be overridden
        config["MODULES"] = ["tests.core.modules.b", "tests.core.modules.b2_invalid"]
        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config=config)).start()

        # Test loading all modules, and sorting by priority
        config["MODULES"] = ["tests.core.modules.a", "tests.core.modules.b", "tests.core.modules.a2"]
        app = SuperdeskAsyncApp(MockWSGI(config=config))
        app.start()
        modules = app.get_module_list()
        self.assertEqual(len(modules), 2)
        self.assertEqual([m.name for m in modules], ["tests.module_b", "tests.module_a"])

    def test_invalid_modules(self):
        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.c_invalid"]})).start()

        with self.assertRaises(RuntimeError):
            SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.d_invalid"]})).start()

    @mock.patch("tests.core.modules.a.module.init")
    def test_module_init(self, init):
        app = SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.a"]}))
        app.start()
        init.assert_called_once_with(app)

    def test_register_privileges(self):
        app = SuperdeskAsyncApp(MockWSGI(config={"MODULES": ["tests.core.modules.module_with_privileges"]}))
        app.start()

        # check privileges are registered
        registered_privileges = app.privileges.get_all()
        self.assertEqual(len(registered_privileges), 2)
        self.assertTrue(app.privileges.is_locked)

        # after app is started, trying to register a privilege raise an exception
        with self.assertRaises(RuntimeError) as exc:
            app.privileges.add(Privilege(name="After app started"))
            self.assertEqual(exc.msg, "Cannot add privileges after the app has started")