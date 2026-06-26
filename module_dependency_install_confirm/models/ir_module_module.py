# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.addons.base.models.ir_module import assert_log_admin_access

from ..const import SKIP_DEPENDENCY_CONFIRMATION


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _get_dependency_confirmation_excluded_states(self):
        return ("installed", "uninstallable", "to remove")

    def _sort_dependency_confirmation_modules(self, modules):
        return modules.sorted(
            lambda module: (
                (module.shortdesc or module.name or "").lower(),
                module.name or "",
            )
        )

    def _get_dependency_confirmation_direct_modules(self):
        excluded_states = self._get_dependency_confirmation_excluded_states()
        dependencies = self.dependencies_id.depend_id - self
        dependencies = dependencies.filtered(
            lambda module: module.state not in excluded_states
        )
        return self._sort_dependency_confirmation_modules(dependencies)

    def _get_dependency_confirmation_modules(self):
        excluded_states = self._get_dependency_confirmation_excluded_states()
        dependencies = self.browse()
        seen = self
        pending = self.dependencies_id.depend_id - seen
        while pending:
            module = pending[:1]
            pending -= module
            if module in seen:
                continue
            seen |= module
            if module.state not in excluded_states:
                dependencies |= module
                pending |= module.dependencies_id.depend_id - seen
        return self._sort_dependency_confirmation_modules(dependencies)

    def _get_dependency_confirmation_transitive_modules(self):
        direct_dependencies = self._get_dependency_confirmation_direct_modules()
        dependencies = self._get_dependency_confirmation_modules() - direct_dependencies
        return self._sort_dependency_confirmation_modules(dependencies)

    def _get_dependency_confirmation_action(self, operation):
        dependencies = self._get_dependency_confirmation_direct_modules()
        transitive_dependencies = self._get_dependency_confirmation_transitive_modules()
        wizard = self.env["module.dependency.install.confirm"].create(
            {
                "operation": operation,
                "module_ids": [(6, 0, self.ids)],
                "dependency_ids": [(6, 0, dependencies.ids)],
                "transitive_dependency_ids": [(6, 0, transitive_dependencies.ids)],
            }
        )
        action_name = (
            _("Confirm Module Installation")
            if operation == "install"
            else _("Confirm Module Upgrade")
        )
        return {
            "type": "ir.actions.act_window",
            "name": action_name,
            "res_model": "module.dependency.install.confirm",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def _should_confirm_dependency_installation(self):
        return (
            not self.env.context.get(SKIP_DEPENDENCY_CONFIRMATION)
            and bool(self._get_dependency_confirmation_direct_modules())
        )

    @assert_log_admin_access
    def button_immediate_install(self):
        if self._should_confirm_dependency_installation():
            return self._get_dependency_confirmation_action("install")
        return super().button_immediate_install()

    @assert_log_admin_access
    def button_immediate_upgrade(self):
        if self._should_confirm_dependency_installation():
            return self._get_dependency_confirmation_action("upgrade")
        return super().button_immediate_upgrade()