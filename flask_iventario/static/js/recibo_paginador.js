/* ==========================================================
   PAGINADOR DEL RECIBO
   ----------------------------------------------------------
   Reparte las filas de productos en hojas de altura fija y clona
   el encabezado y el pie completo en CADA una.

   Se pagina a mano en vez de dejárselo al navegador porque ni
   <tfoot> ni un pie "position: fixed" se repiten de forma fiable
   entre versiones de Chrome (Chromium 141 no repite ninguno de los
   dos), y aquí el bloque de firmas y totales tiene que salir sí o
   sí en todas las páginas.

   La geometría se lee de los data-* de #reciboPaginado:
     data-margen-sup, data-margen-inf, data-margen-lat  (en cm)
   y de ahí salen las variables CSS y la regla @page.

   Requiere en el DOM:
     #reciboPaginado      contenedor destino (vacío)
     #plantillaColumnas   <colgroup> con los anchos de columna
     #plantillaEncabezado <thead> a clonar en cada página
     #plantillaFilas      <tbody> con todas las filas de productos
     #plantillaPie        bloque de firmas + totales
   ========================================================== */
(function () {
    'use strict';

    var HOJA = { ancho: 21.59, alto: 27.94 };   // carta vertical, en cm

    /* Colchón en píxeles para absorber redondeos del navegador al medir. */
    var COLCHON_PX = 4;

    function contenedor() {
        return document.getElementById('reciboPaginado');
    }

    function geometria() {
        var c = contenedor();
        return {
            sup: parseFloat(c.dataset.margenSup),
            inf: parseFloat(c.dataset.margenInf),
            lat: parseFloat(c.dataset.margenLat)
        };
    }

    /* Propaga los márgenes a las variables CSS y a la regla @page.
       Una regla @page no puede depender de una clase, por eso se
       reescribe el contenido de <style id="reglaPagina">. */
    function aplicarGeometria() {
        var m = geometria();
        var altoUtil = HOJA.alto - m.sup - m.inf;

        var raiz = document.documentElement;
        raiz.style.setProperty('--margen-sup', m.sup + 'cm');
        raiz.style.setProperty('--margen-inf', m.inf + 'cm');
        raiz.style.setProperty('--margen-lat', m.lat + 'cm');
        raiz.style.setProperty('--alto-util', altoUtil + 'cm');

        var estilo = document.getElementById('reglaPagina');
        if (estilo) {
            estilo.textContent = '@page { size: letter portrait; margin: ' +
                m.sup + 'cm ' + m.lat + 'cm ' + m.inf + 'cm ' + m.lat + 'cm; }';
        }
        return altoUtil;
    }

    /* Cuántos píxeles CSS mide un centímetro en este navegador
       (normalmente 37.795, pero se mide en vez de asumirlo). */
    function pixelesPorCm() {
        var sonda = document.createElement('div');
        sonda.style.cssText = 'position:absolute;visibility:hidden;width:10cm;height:0;';
        document.body.appendChild(sonda);
        var px = sonda.getBoundingClientRect().width / 10;
        document.body.removeChild(sonda);
        return px;
    }

    /* Los clones no pueden arrastrar los id de las plantillas. */
    function sinIds(nodo) {
        if (nodo.removeAttribute) { nodo.removeAttribute('id'); }
        var conId = nodo.querySelectorAll ? nodo.querySelectorAll('[id]') : [];
        for (var i = 0; i < conId.length; i++) {
            conId[i].removeAttribute('id');
        }
        return nodo;
    }

    function paginar() {
        var cont = contenedor();
        var plantillaColumnas = document.getElementById('plantillaColumnas');
        var plantillaEncabezado = document.getElementById('plantillaEncabezado');
        var plantillaFilas = document.getElementById('plantillaFilas');
        var plantillaPie = document.getElementById('plantillaPie');
        if (!cont || !plantillaEncabezado || !plantillaFilas || !plantillaPie) { return; }

        var altoUtilPx = aplicarGeometria() * pixelesPorCm() - COLCHON_PX;
        var filas = plantillaFilas.children;

        cont.innerHTML = '';
        cont.classList.add('midiendo');

        /* Devuelve referencias directas. Ojo: NO usar querySelector('tbody')
           sobre la hoja — el encabezado del cliente lleva una tabla anidada
           cuyo <tbody> implícito aparece antes en el orden del documento. */
        
        var descuentoGlobal = parseFloat(cont.dataset.descuentoGlobal) || 0;
        var totalBrutoVenta = parseFloat(cont.dataset.totalBruto) || 0;
        var descuentoAcumulado = 0;
        var hojasCreadas = [];

        function nuevaHoja() {
            var hoja = document.createElement('section');
            hoja.className = 'hoja';

            var caja = document.createElement('div');
            caja.className = 'hoja-contenido';

            var tabla = document.createElement('table');
            tabla.className = 'table-custom';
            if (plantillaColumnas) {
                tabla.appendChild(sinIds(plantillaColumnas.cloneNode(true)));
            }
            tabla.appendChild(sinIds(plantillaEncabezado.cloneNode(true)));

            var cuerpo = document.createElement('tbody');
            tabla.appendChild(cuerpo);

            caja.appendChild(tabla);
            var pie = sinIds(plantillaPie.cloneNode(true));
            caja.appendChild(pie);
            hoja.appendChild(caja);
            cont.appendChild(hoja);
            
            var objHoja = { hoja: hoja, caja: caja, cuerpo: cuerpo, pie: pie };
            hojasCreadas.push(objHoja);
            return objHoja;
        }
var pagina = nuevaHoja();

        for (var i = 0; i < filas.length; i++) {
            var fila = filas[i].cloneNode(true);
            pagina.cuerpo.appendChild(fila);

            if (pagina.caja.getBoundingClientRect().height > altoUtilPx) {
                /* No cabe: si la hoja ya tenía otras filas, esta pasa a la
                   siguiente. Si era la única, se deja: una fila más alta que
                   la página no tiene dónde ir, y dejarla evita un bucle. */
                if (pagina.cuerpo.children.length > 1) {
                    pagina.cuerpo.removeChild(fila);
                    pagina = nuevaHoja();
                    pagina.cuerpo.appendChild(fila);
                }
            }
        }

        
        cont.classList.remove('midiendo');
        
        /* ------------------------------------------------------------------
           Totales por página.

           Cada hoja muestra los importes de SUS productos, no los de la
           factura entera: con el pie repetido idéntico en las cuatro hojas
           parecía que el cliente debía cuatro veces el total.

           Regla de redondeo: se redondea CADA componente a 2 decimales y los
           agregados se derivan de los ya redondeados. Sumando los valores sin
           redondear y formateando al final, la columna no cuadraba —una hoja
           imprimía Base 559,54 + IGTF 16,79 + IVA 89,53 = 665,86 y un TOTAL
           de 665,85— y la suma de las páginas se quedaba en 961,49 frente a
           los 961,50 de la factura.
           ------------------------------------------------------------------ */
        /* Si no hay huecos que rellenar (comprobante de ajuste manual, que no
           lleva desglose de impuestos) no hay nada que calcular. */
        if (plantillaPie.querySelector('.val-base-imponible')) {
            for (var j = 0; j < hojasCreadas.length; j++) {
                var esUltima = (j === hojasCreadas.length - 1);
                var obj = hojasCreadas[j];
                var filasHoja = obj.cuerpo.children;

                var montoBrutoPagina = 0;
                for (var k = 0; k < filasHoja.length; k++) {
                    montoBrutoPagina += parseFloat(filasHoja[k].getAttribute('data-precio-total')) || 0;
                }
                montoBrutoPagina = redondear(montoBrutoPagina);

                /* El descuento global se reparte a prorrata del bruto de cada
                   hoja. La última se queda con lo que falte para completar el
                   descuento exacto, así las páginas suman la factura al céntimo. */
                var descuentoPagina = 0;
                if (descuentoGlobal > 0 && totalBrutoVenta > 0) {
                    if (esUltima) {
                        descuentoPagina = redondear(descuentoGlobal - descuentoAcumulado);
                    } else {
                        descuentoPagina = redondear(descuentoGlobal * (montoBrutoPagina / totalBrutoVenta));
                        descuentoAcumulado = redondear(descuentoAcumulado + descuentoPagina);
                    }
                }

                var baseImponible = redondear(montoBrutoPagina - descuentoPagina);
                var igtf = redondear(baseImponible * 0.03);
                var iva = redondear(baseImponible * 0.16);
                var subtotal = redondear(baseImponible + igtf);
                var total = redondear(subtotal + iva);

                escribir(obj.pie, '.val-monto-bruto', moneda(montoBrutoPagina));
                escribir(obj.pie, '.val-descuento', '-' + moneda(descuentoPagina));
                escribir(obj.pie, '.val-base-imponible', moneda(baseImponible));
                escribir(obj.pie, '.val-igtf', moneda(igtf));
                escribir(obj.pie, '.val-subtotal', moneda(subtotal));
                escribir(obj.pie, '.val-iva', moneda(iva));
                escribir(obj.pie, '.val-total', moneda(total));
                escribir(obj.pie, '.val-total-grande', moneda(total));
            }
        }
    }

    function redondear(n) {
        return Math.round(n * 100) / 100;
    }

    /* Formato venezolano: punto para los miles, coma para los decimales. */
    function moneda(n) {
        var partes = Math.abs(n).toFixed(2).split('.');
        partes[0] = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        return (n < 0 ? '-' : '') + partes[0] + ',' + partes[1];
    }

    function escribir(pie, selector, texto) {
        var el = pie.querySelector(selector);
        if (el) { el.textContent = texto; }
    }


    /* Se expone para poder repaginar desde el template si hiciera falta. */
    window.paginarRecibo = paginar;

    document.addEventListener('DOMContentLoaded', paginar);
    /* Las fuentes pueden cargar después del DOM y cambiar la altura de las
       filas: se repagina cuando todo esté listo y antes de imprimir. */
    window.addEventListener('load', paginar);
    window.addEventListener('beforeprint', paginar);
})();
