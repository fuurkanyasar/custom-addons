# -*- coding: utf-8 -*-

from lxml import etree

from odoo.tests.common import TransactionCase


class TestModuleDependencyInstallConfirmation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Module = cls.env["ir.module.module"]
        cls.Dependency = cls.env["ir.module.module.dependency"]

    def _create_module(self, name, state="uninstalled", depends=None, shortdesc=None):
        module = self.Module.create(
            {
                "name": name,
                "shortdesc": shortdesc or name,
                "state": state,
            }
        )
        for dependency_name in depends or []:
            self.Dependency.create(
                {
                    "module_id": module.id,
                    "name": dependency_name,
                }
            )
        return module

    def test_dependency_tree_ignores_installed_modules(self):
        installed = self._create_module(
            "x_confirm_installed_dep",
            state="installed",
        )
        leaf = self._create_module("x_confirm_leaf_dep")
        middle = self._create_module(
            "x_confirm_middle_dep",
            depends=[leaf.name],
        )
        module = self._create_module(
            "x_confirm_target",
            depends=[middle.name, installed.name],
        )

        dependencies = module._get_dependency_confirmation_modules()

        self.assertEqual(
            set(dependencies.mapped("name")),
            {"x_confirm_leaf_dep", "x_confirm_middle_dep"},
        )

    def test_direct_dependencies_are_separated_from_full_dependency_chain(self):
        direct = self._create_module("x_confirm_direct_dep")
        leaf = self._create_module("x_confirm_leaf_chain_dep")
        middle = self._create_module(
            "x_confirm_middle_chain_dep",
            depends=[leaf.name],
        )
        installed = self._create_module(
            "x_confirm_installed_chain_dep",
            state="installed",
        )
        module = self._create_module(
            "x_confirm_direct_target",
            depends=[direct.name, middle.name, installed.name],
        )

        direct_dependencies = module._get_dependency_confirmation_direct_modules()
        chain_dependencies = module._get_dependency_confirmation_transitive_modules()

        self.assertEqual(
            set(direct_dependencies.mapped("name")),
            {"x_confirm_direct_dep", "x_confirm_middle_chain_dep"},
        )
        self.assertEqual(
            set(chain_dependencies.mapped("name")),
            {"x_confirm_leaf_chain_dep"},
        )

    def test_install_button_returns_confirmation_action_when_dependencies_are_missing(self):
        dependency = self._create_module("x_confirm_install_dep")
        module = self._create_module(
            "x_confirm_install_target",
            depends=[dependency.name],
        )

        action = module.button_immediate_install()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "module.dependency.install.confirm")
        self.assertEqual(action["target"], "new")
        self.assertEqual(wizard.operation, "install")
        self.assertEqual(wizard.module_ids, module)
        self.assertEqual(wizard.dependency_ids, dependency)
        self.assertFalse(wizard.transitive_dependency_ids)

    def test_install_confirmation_action_keeps_dependency_chain_optional(self):
        leaf = self._create_module("x_confirm_action_leaf_dep")
        direct = self._create_module(
            "x_confirm_action_direct_dep",
            depends=[leaf.name],
        )
        module = self._create_module(
            "x_confirm_action_target",
            depends=[direct.name],
        )

        action = module.button_immediate_install()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(wizard.dependency_ids, direct)
        self.assertEqual(wizard.transitive_dependency_ids, leaf)
        self.assertFalse(wizard.show_full_dependency_chain)

    def test_upgrade_button_returns_confirmation_action_for_new_dependency(self):
        dependency = self._create_module("x_confirm_upgrade_dep")
        module = self._create_module(
            "x_confirm_upgrade_target",
            state="installed",
            depends=[dependency.name],
        )

        action = module.button_immediate_upgrade()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "module.dependency.install.confirm")
        self.assertEqual(action["target"], "new")
        self.assertEqual(wizard.operation, "upgrade")
        self.assertEqual(wizard.module_ids, module)
        self.assertEqual(wizard.dependency_ids, dependency)

    def test_confirmation_view_uses_v19_module_kanban(self):
        view = self.env.ref(
            "module_dependency_install_confirm."
            "view_module_dependency_install_confirm_form"
        )
        arch = etree.fromstring(view.arch_db.encode())

        self.assertFalse(arch.xpath("//*[@attrs]"))
        self.assertTrue(arch.xpath("//field[@name='show_full_dependency_chain']"))
        self.assertTrue(
            arch.xpath(
                "//div[@invisible=\"not show_full_dependency_chain "
                "or not has_transitive_dependency_ids\"]"
            )
        )

        for field_name in ("module_ids", "dependency_ids", "transitive_dependency_ids"):
            field = arch.xpath("//field[@name='%s']" % field_name)[0]
            self.assertEqual(field.get("mode"), "kanban")
            self.assertIn("o_modules_field", field.get("class", "").split())
            self.assertFalse(field.xpath("./tree|./list"))
            self.assertTrue(
                field.xpath("./kanban[contains(@class, 'o_modules_kanban')]")
            )
            self.assertTrue(field.xpath(".//t[@t-name='card']"))
            self.assertTrue(
                field.xpath(".//field[@name='icon' and @widget='image_url']")
            )
