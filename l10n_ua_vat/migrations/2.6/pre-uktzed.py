from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute("UPDATE product_product AS p SET ukt_zed = pc.name FROM product_classification AS pc WHERE p.ukt_zed_id = pc.id")
    cr.execute("DELETE FROM product_classification")
