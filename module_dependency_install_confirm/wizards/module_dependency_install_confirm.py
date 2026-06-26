# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

from ..const import SKIP_DEPENDENCY_CONFIRMATION


class ModuleDependencyInstallConfirm(models.TransientModel):
    _name = "module.dependency.install.confirm"
    _description = "Module Dependency Install Confirmation"

    operation = fields.Selection(
        selection=[
            ("install", "Install"),
            ("upgrade", "Upgrade"),
        ],
        required=True,
        readonly=True,
    )
    module_ids = fields.Many2many(
        comodel_name="ir.module.module",
        relation="module_dependency_install_confirm_module_rel",
        column1="wizard_id",
        column2="module_id",
        string="Selected Modules",
        readonly=True,
    )
    dependency_ids = fields.Many2many(
        comodel_name="ir.module.module",
        relation="module_dependency_install_confirm_dependency_rel",
        column1="wizard_id",
        column2="module_id",
        string="Required Modules",
        readonly=True,
    )
    transitive_dependency_ids = fields.Many2many(
        comodel_name="ir.module.module",
        relation="module_dependency_install_confirm_transitive_dependency_rel",
        column1="wizard_id",
        column2="module_id",
        string="Also Installed Through Dependencies",
        readonly=True,
    )
    show_full_dependency_chain = fields.Boolean(
        string="Show full dependency chain",
        default=False,
    )
    has_transitive_dependency_ids = fields.Boolean(
        compute="_compute_has_transitive_dependency_ids",
    )
    title = fields.Char(compute="_compute_text")
    message = fields.Text(compute="_compute_text")

    @api.depends("transitive_dependency_ids")
    def _compute_has_transitive_dependency_ids(self):
        for wizard in self:
            wizard.has_transitive_dependency_ids = bool(
                wizard.transitive_dependency_ids
            )

    @api.depends("operation", "module_ids", "dependency_ids", "transitive_dependency_ids")
    def _compute_text(self):
        for wizard in self:
            dependency_count = len(wizard.dependency_ids)
            transitive_count = len(wizard.transitive_dependency_ids)
            chain_message = ""
            if transitive_count:
                chain_message = _(
                    " Enable Show full dependency chain to review %s additional "
                    "module(s) installed through these requirements."
                ) % transitive_count
            if wizard.operation == "upgrade":
                wizard.title = _("Module upgrade confirmation")
                wizard.message = _(
                    "Upgrading the selected module will also install %s required "
                    "module(s). These modules may add new models, menus, access "
                    "rights, and features to this database."
                ) % dependency_count + chain_message
            else:
                wizard.title = _("Module installation confirmation")
                wizard.message = _(
                    "Installing the selected module will also install %s required "
                    "module(s). These modules may add new models, menus, access "
                    "rights, and features to this database."
                ) % dependency_count + chain_message

    def action_continue(self):
        self.ensure_one()
        modules = self.module_ids.with_context(
            **{SKIP_DEPENDENCY_CONFIRMATION: True}
        )
        if self.operation == "upgrade":
            return modules.button_immediate_upgrade()
        return modules.button_immediate_install()