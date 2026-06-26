# -*- coding: utf-8 -*-

{
    "name": "Module Dependency Install Confirmation",
    "version": "19.0.1.0.0",
    "category": "Administration",
    "summary": "Warn users before installing dependencies during module install or upgrade.",
    "author": "Furkan Yasar",
    "license": "Other proprietary",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/module_dependency_install_confirm_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
