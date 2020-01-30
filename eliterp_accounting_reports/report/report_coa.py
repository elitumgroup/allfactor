from odoo import models, api, _, fields
from datetime import datetime

from odoo.tools import pycompat


class CoaReport(models.AbstractModel):
    _inherit = "account.coa.report"

    def _get_super_columns(self, options):
        """Si un key tipo string no lo es lo actualizamos la fuerza."""
        rec = super(CoaReport, self)._get_super_columns(options)
        for col in rec.get('columns', []):
            if not isinstance(col.get('string', ''), str):
                col['string'] = str(col['string'])
        return rec
