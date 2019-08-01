/* ========================================================================
 * Copyright (c) 2018 Oleksandr Komarov, Modool (https://modool.pro)
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
 * ======================================================================== */
odoo.define('pos_blackbox_ua.screens', function (require) {
"use strict";

/* This module redefine data, which POSTed to BlockBox via func print_receipt(data)
 It's needed to print them in Fiscal Printer format.
 */

var screens = require('point_of_sale.screens');

var _t  = require('web.core')._t;

/*--------------------------------------*\
 |         THE RECEIPT SCREEN           |
\*======================================*/

// The receipt screen displays the order's
// receipt and allows it to be printed in a web browser.
// The receipt screen is not shown if the point of sale
// is set up to print with the proxy. Altough it could
// be useful to do so...

screens.ReceiptScreenWidget.include({
    print_xml: function() {
        var proxy_status = this.pos.proxy.get('status');
        if (proxy_status.status != 'connected'){
            this.gui.show_popup('error',{
                'title': _t('Do not Connected with Fiscal BlackBox'),
                'body': _t('Check power of Fiscal BlackBox.\nContact with system administrator if it not helped.'),
            });
            return;
        }else if (!proxy_status.drivers){
            this.gui.show_popup('error',{
                'title': _t('POS fiscal drivers do not loaded'),
                // https://modool.pro
                'body': _t('Contact with system administrator.'),
            });
            return;
        }else if (!proxy_status.drivers.fiscalpos){
            this.gui.show_popup('error',{
                'title': _t('Please use Fiscal BlackBox module'),
                // https://modool.pro
                'body': _t('Contact with system administrator.'),
            });
            return;
        }else if (proxy_status.drivers.fiscalpos.status != 'connected'){
            this.gui.show_popup('error',{
                'title': _t('Do not Connected with Fiscal printer'),
                'body': _t('Check power of Fiscal printer.\nContact with system administrator if it not helped.'),
            });
            return;
        };
        // get structure of data for Ukrainian fiscal printing
        var receipt = this.get_receipt_render_env().order.export_for_printing();

        // remove company logo, because it is a big, unnecessary data for transfer
        delete receipt.logo;
        this.pos.proxy.print_receipt(receipt);
        this.pos.get_order()._printed = true;
    },
});

});
