# -*- coding: utf-8 -*-
# This file is part of the party_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.exceptions import UserError


class CompanyNotDefined(UserError):
    pass


class VatNumberNotFound(UserError):
    pass
