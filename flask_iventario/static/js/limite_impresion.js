/* ==========================================================
   AVISO DE LÍMITE DE IMPRESIÓN
   ----------------------------------------------------------
   Los campos que acaban en una columna de un impreso (el nombre
   y el código del repuesto en el recibo) se recortan con puntos
   suspensivos cuando no caben. El formulario admite mucho más
   texto del que entra, así que quien registra el producto no se
   entera hasta que ve la factura ya impresa.

   Este módulo mide el texto con la MISMA tipografía del impreso
   y avisa debajo del campo. Es solo informativo: nunca bloquea
   el guardado ni recorta lo que el usuario escribe.

   El límite es de ANCHO, no de caracteres: en Arial una "M" mide
   9,2 px y una "I" 3,1 px. Por eso se mide el texto real en vez
   de poner un maxlength, que penalizaría los nombres de letras
   estrechas y aun así dejaría pasar algunos anchos.

   Uso: añadir al input/textarea los atributos
     data-limite-cm="10.95"                     (obligatorio) ancho útil de la columna
     data-limite-fuente="11px Arial"            (por defecto 11px Arial)
     data-limite-mayusculas="true"              si el impreso aplica text-transform
     data-limite-quitar-prefijo="CÓDIGO: "      prefijo que el impreso no muestra
     data-limite-donde="el recibo"              cómo nombrarlo en el aviso

   Los cm salen del <colgroup> de templates/recibo.html: ancho útil
   19.59cm, descripción 57% -> 11.17cm menos 8px de padding = 10.95cm;
   código 15% -> 2.94cm menos padding = 2.73cm.
   ========================================================== */
(function () {
    'use strict';

    var PX_POR_CM = 96 / 2.54;          // 37.7953, la conversión que usa el navegador
    var lienzo = document.createElement('canvas').getContext('2d');
    var registrados = [];

    var COLOR_OK = '#6c757d';           // gris apagado
    var COLOR_AVISO = '#997404';        // ámbar legible sobre blanco

    function medir(texto, fuente) {
        lienzo.font = fuente;
        return lienzo.measureText(texto).width;
    }

    /* Deja el texto tal y como lo va a pintar el impreso. */
    function textoImpreso(campo) {
        var v = campo.value || '';
        var prefijo = campo.dataset.limiteQuitarPrefijo;
        if (prefijo && v.toUpperCase().indexOf(prefijo.toUpperCase()) === 0) {
            v = v.slice(prefijo.length);
        }
        v = v.replace(/\s+/g, ' ').trim();
        if (campo.dataset.limiteMayusculas === 'true') {
            v = v.toUpperCase();
        }
        return v;
    }

    /* Prefijo que quedaría visible antes de los puntos suspensivos.
       Búsqueda binaria: el ancho crece con la longitud, así que basta. */
    function parteVisible(texto, anchoPx, fuente) {
        var disponible = anchoPx - medir('…', fuente);
        var bajo = 0, alto = texto.length;
        while (bajo < alto) {
            var medio = Math.ceil((bajo + alto) / 2);
            if (medir(texto.slice(0, medio), fuente) <= disponible) { bajo = medio; }
            else { alto = medio - 1; }
        }
        return texto.slice(0, bajo);
    }

    function actualizar(campo, aviso) {
        var fuente = campo.dataset.limiteFuente || '11px Arial';
        var anchoPx = parseFloat(campo.dataset.limiteCm) * PX_POR_CM;
        var donde = campo.dataset.limiteDonde || 'el recibo';
        var texto = textoImpreso(campo);

        aviso.textContent = '';
        aviso.style.color = COLOR_OK;

        if (!texto) { return; }

        if (medir(texto, fuente) <= anchoPx) {
            aviso.textContent = texto.length + ' caracteres · entra completo en ' + donde;
            return;
        }

        // No cabe: se muestra exactamente dónde cae el corte.
        aviso.style.color = COLOR_AVISO;
        var intro = document.createElement('span');
        intro.textContent = texto.length + ' caracteres · en ' + donde + ' se verá hasta aquí: ';
        var muestra = document.createElement('strong');
        muestra.textContent = '“' + parteVisible(texto, anchoPx, fuente) + '…”';
        aviso.appendChild(intro);
        aviso.appendChild(muestra);
    }

    function iniciar() {
        var campos = document.querySelectorAll('[data-limite-cm]');
        for (var i = 0; i < campos.length; i++) {
            var campo = campos[i];
            if (campo.dataset.limiteListo === 'true') { continue; }
            campo.dataset.limiteListo = 'true';

            var aviso = document.createElement('div');
            aviso.className = 'form-text';
            aviso.style.color = COLOR_OK;
            campo.insertAdjacentElement('afterend', aviso);

            (function (c, a) {
                var refrescar = function () { actualizar(c, a); };
                c.addEventListener('input', refrescar);
                c.addEventListener('change', refrescar);
                registrados.push(refrescar);
                refrescar();
            })(campo, aviso);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', iniciar);
    } else {
        iniciar();
    }

    /* Si la tipografía termina de cargar después, las medidas cambian. */
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(function () {
            for (var i = 0; i < registrados.length; i++) { registrados[i](); }
        });
    }
})();
