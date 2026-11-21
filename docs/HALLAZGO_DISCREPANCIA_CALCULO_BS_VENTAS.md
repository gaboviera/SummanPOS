# Hallazgo: Discrepancia en el Cálculo de Totales en Bolívares (Bs.) en Punto de Venta (`/ventas`)

## 1. Resumen del Problema
En la interfaz del punto de venta (`/ventas` -> `templates/ventas.html`), existe una discrepancia visible entre el monto total en bolívares mostrado en el carrito principal (panel inferior derecho) y el monto total en bolívares calculado en el modal **"Procesar Venta"** (cabecera del modal y campo de la calculadora rápida).

### Caso de Prueba Real (Evidencia en Captura):
* **Venta:** 2 unidades de un producto con costo y precio de **$73,95 USD** cada uno.
* **Tasa utilizada (USDT):** `955,90 Bs/$`.
* **Total en USD:** `$176,00`.
* **Monto en el Carrito (Abajo a la derecha):** `USDT 176.00` | **`168.239,36 Bs.`**
* **Monto en el Modal "Procesar Venta" (Cabecera y campo):** `$176.00` | **`168.238,40 Bs.`**
* **Diferencia / Descuadre:** **`0,96 Bs.`** (casi 1 Bolívar completo).

---

## 2. Causa Raíz (Root Cause Analysis)

El problema radica en que el frontend (`templates/ventas.html`) utiliza **dos métodos de cálculo divergentes** para determinar el total en bolívares de una misma venta:

### A. Método del Carrito Principal (`renderizarCarrito`): Suma de Componentes Convertidos
En las líneas 620-637 de `templates/ventas.html`, el carrito calcula cada componente fiscal en USD, lo convierte a Bs de forma individual con `calcSecundario()`, lo redondea a 2 decimales y luego suma los resultados redondeados:

```javascript
// templates/ventas.html (líneas 625-635)
const redondear = (n) => Math.round(n * 100) / 100;
const baseImponibleBs = redondear(calcSecundario(baseImponible)); // 147.90 * 955.90 = 141.377,61 Bs.
const igtfBs = redondear(calcSecundario(igtf));                   // 4.437 * 955.90 = 4.241,33 Bs.
const ivaBs = redondear(calcSecundario(iva));                     // 23.664 * 955.90 = 22.620,42 Bs.
const subTotalBs = redondear(baseImponibleBs + igtfBs);           // 141.377,61 + 4.241,33 = 145.618,94 Bs.
const totalPagarBs = redondear(subTotalBs + ivaBs);               // 145.618,94 + 22.620,42 = 168.239,36 Bs.
```

### B. Método del Modal "Procesar Venta" (`pago_metodo` change event): Conversión Directa del Total
En las líneas 860-877 y 795-802 de `templates/ventas.html`, cuando se selecciona un método en bolívares (Pago Móvil, Transferencia Bs, etc.), el modal toma el total ya redondeado en dólares (`$176,00`) y lo multiplica directamente por la tasa:

```javascript
// templates/ventas.html (líneas 862-864)
const totalUsdStr = document.getElementById('totalCobrar').getAttribute('data-usd'); // "176.00"
const totalUsd = parseFloat(totalUsdStr);
const totalBs = totalUsd * tasaAplicar; // 176.00 * 955.90 = 168.238,40 Bs.
document.getElementById('modalTotalCobrar').innerHTML = `$${totalUsd.toFixed(2)} <br><small class="text-success fs-5">${totalBs.toFixed(2)} Bs.</small>`;

// Y en la calculadora rápida (líneas 848-850):
let ms = montoUsd * tasaAplicar; // 176.00 * 955.90 = 168.238,40 Bs.
document.getElementById('pago_monto_ms').value = ms.toFixed(2);
```

---

## 3. Demostración Matemática del Descuadre

1. **En dólares (USD):**
   * Base Imponible: $2 	imes 73,95 = \$147,90$
   * Impuestos (IGTF 3% + IVA 16% = 19%):  
     $$147{,}90 	imes 1{,}19 = \mathbf{\$176{,}001\text{ USD}}$$
   * En dólares se formatea a 2 decimales: `176.00` (se truncan/redondean los $+0,001$ centavos).

2. **El impacto de la tasa de cambio alta (955,90 Bs/$):**
   * El residuo de **$0,001 USD** que se descarta en el redondeo a 2 decimales en dólares, al multiplicarse por la tasa equivale a:
     $$0{,}001 	imes 955{,}90 = \mathbf{0{,}9559\text{ Bs.} \approx 0{,}96\text{ Bs.}}$$
   * **Método Directo (Modal):**  
     $$176{,}00 	imes 955{,}90 = \mathbf{168.238{,}40\text{ Bs.}}$$
   * **Método por Componentes (Carrito):**  
     $$147{,}90 	imes 1{,}19 	imes 955{,}90 = \mathbf{168.239{,}36\text{ Bs.}}$$
   * **Diferencia exacta:**  
     $$168.239{,}36 - 168.238{,}40 = \mathbf{0{,}96\text{ Bs.}}$$

---

## 4. Impacto Operativo
* **Confusión visual:** El cajero ve `168.239,36 Bs.` en la pantalla principal pero al abrir el cobro la calculadora le dice `168.238,40 Bs.`.
* **Riesgo de saldo pendiente ficticio:** Si el cliente paga los `168.238,40 Bs.` que sugiere la calculadora, al registrar el pago en el sistema:
  `168.238,40 / 955,90 = 176,00 $`. En dólares el saldo queda en `$0,00`, pero si se validara contra los Bs del carrito parecería faltar `0,96 Bs.`.

---

## 5. Archivos Afectados en el Repositorio

* **`flask_iventario/templates/ventas.html`:**
  * **Líneas 625–640:** Función `renderizarCarrito()`, cálculo de `baseImponibleBs`, `igtfBs`, `ivaBs`, `subTotalBs` y `totalPagarBs`.
  * **Líneas 795–802:** Evento de actualización de la calculadora rápida de montos secundarios (`pago_monto` -> `pago_monto_ms`).
  * **Líneas 845–878:** Listener `pago_metodo.addEventListener('change', ...)` donde se calcula `totalBs = totalUsd * tasaAplicar` y se inyecta en `#modalTotalCobrar`.
  * **Líneas 1010–1025:** Al abrir `#modalProcesarPago`, se sincroniza `#modalTotalCobrar` desde `#totalCobrar`.

---

## 6. Opciones de Solución para Claude

### Opción A (Recomendada: Unificar bajo la Fuente de Verdad del Carrito)
Hacer que el modal y su calculadora rápida utilicen el `totalPagarBs` ya calculado por el carrito (`#totalCobrar`) en lugar de recalcular `totalUsd * tasaAplicar` desde cero.

* **Ventajas:**
  * Garantiza 100% de coherencia visual: lo que ve el cajero en el resumen del pedido es exactamente lo que se llena en la calculadora de pago móvil / transferencia.
  * La suma desglose (Base + IGTF + IVA en Bs) coincide con el total en Bs.
* **Implementación:**
  1. Almacenar el total en Bs en un atributo de datos en `#totalCobrar`, por ejemplo `data-bs="${totalPagarBs.toFixed(2)}"`.
  2. En el modal, cuando el método de pago requiera bolívares y el usuario vaya a pagar el 100% del saldo, tomar `document.getElementById('totalCobrar').getAttribute('data-bs')`.

### Opción B (Alinear el Carrito al Total Redondeado en USD)
Hacer que el total general en bolívares del carrito (`totalPagarBs`) sea calculado directamente como `totalPagar * tasa`, y ajustar el centavo de diferencia en el IVA o en la Base para que la columna sume igual.

* **Ventajas:**
  * Si el precio de venta acordado es exactamente `$176,00 USD`, pagar en Bs equivale a `$176,00 	imes \text{tasa}$`.
* **Desventajas:**
  * Requiere lógica de ajuste de redondeo de centavos (*penny rounding reconciliation*) en los renglones fiscales secundarios.

---

## 7. Criterios de Aceptación para la Solución
1. Para cualquier venta en `/ventas`, el monto en Bs mostrado en `TOTAL A PAGAR` del carrito debe ser **idéntico al centavo** al monto en Bs mostrado en `TOTAL A COBRAR` del modal.
2. El campo `Monto a Pagar en Bs:` de la calculadora rápida debe autocompletarse con ese mismo valor exacto.
3. El registro del pago en bolívares debe cubrir el 100% de la venta en dólares sin dejar centavos pendientes (`Resta: $0.00`).
