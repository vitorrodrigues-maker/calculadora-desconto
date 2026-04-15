(function () {
    "use strict";

    const LIMIT_PCT = 0.035;
    const DISCOUNT_CATEGORIES = [
        { key: "vlr_comercial_vendedores", label: "Comercial Vendedores" },
        { key: "vlr_comercial_sups", label: "Comercial Supervisores" },
        { key: "vlr_tag_verde", label: "Tag Verde / Ofertas" },
        { key: "vlr_adf", label: "ADF" },
        { key: "vlr_abre_portas", label: "Abre Portas" },
        { key: "vlr_exclusivo", label: "Exclusivo Campanha" },
        { key: "vlr_ops_realocados", label: "Ops Realocados" },
        { key: "vlr_ops_outros", label: "Ops Outros" },
        { key: "vlr_cupom_app", label: "Cupom APP" },
        { key: "vlr_cupom_prover", label: "Cupom Prover" },
        { key: "vlr_cupom_pap", label: "Cupom PAP" },
        { key: "vlr_cupom_ops", label: "Cupom Ops" },
        { key: "vlr_hcd", label: "HCD" },
    ];

    const COMISSAO_TABLE = [
        { max: 0, rate: 0.03 },
        { max: 0.005, rate: 0.02, tagOnly: true },
        { max: 0.005, rate: 0.02 },
        { max: 0.01, rate: 0.0185 },
        { max: 0.015, rate: 0.017 },
        { max: 0.02, rate: 0.0165 },
        { max: 0.025, rate: 0.015 },
        { max: 0.03, rate: 0.0125 },
        { max: 0.035, rate: 0.01 },
        { max: 0.0405, rate: 0.0075 },
    ];

    let DATA = null;

    // ─── Helpers ────────────────────────────────────────────

    function fmt(v, style) {
        if (v == null || isNaN(v)) return "-";
        if (style === "pct") return (v * 100).toFixed(2) + "%";
        if (style === "pct4") return (v * 100).toFixed(4) + "%";
        if (style === "brl")
            return "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
        return v.toFixed(2);
    }

    function parseNum(el) {
        const v = el.value.replace(/[^\d.,\-]/g, "").replace(",", ".");
        return parseFloat(v) || 0;
    }

    function getToday(dailyRows) {
        const today = new Date().toISOString().slice(0, 10);
        return dailyRows.find((r) => r.order_date_2.slice(0, 10) === today) || dailyRows[dailyRows.length - 1];
    }

    function aggregateMonth(dailyRows) {
        const agg = {
            gmv_fp: 0, vlr_total: 0,
            valor_comissao_dia: 0, gmv_comissionado_dia: 0,
        };
        DISCOUNT_CATEGORIES.forEach((c) => (agg[c.key] = 0));

        dailyRows.forEach((r) => {
            agg.gmv_fp += r.gmv_fp || 0;
            agg.vlr_total += r.vlr_total || 0;
            agg.valor_comissao_dia += r.valor_comissao_dia || 0;
            agg.gmv_comissionado_dia += r.gmv_comissionado_dia || 0;
            DISCOUNT_CATEGORIES.forEach((c) => {
                agg[c.key] += r[c.key] || 0;
            });
        });
        agg.pct_comissao = agg.gmv_comissionado_dia ? agg.valor_comissao_dia / agg.gmv_comissionado_dia : 0;
        return agg;
    }

    function getComissaoRate() {
        return 0.03;
    }

    // ─── Simulation ────────────────────────────────────────

    function simulate(row, gmvPedido, vlrDesconto, pctDesconto) {
        const sim = {};
        const newGmv = row.gmv_fp + gmvPedido;
        const newTotal = row.vlr_total + vlrDesconto;

        DISCOUNT_CATEGORIES.forEach((c) => {
            sim[c.key] = row[c.key] || 0;
        });

        if (pctDesconto <= 0.042) {
            sim.vlr_comercial_vendedores += vlrDesconto;
        } else {
            sim.vlr_comercial_sups += vlrDesconto;
        }

        sim.gmv_fp = newGmv;
        sim.vlr_total = newTotal;

        const newComissaoGmv = (row.gmv_comissionado_dia || 0) + gmvPedido;
        const newComissaoVal = (row.valor_comissao_dia || 0) + gmvPedido * getComissaoRate();
        sim.pct_comissao = newComissaoGmv ? newComissaoVal / newComissaoGmv : 0;
        sim.valor_comissao_dia = newComissaoVal;
        sim.gmv_comissionado_dia = newComissaoGmv;

        return sim;
    }

    // ─── Render discount table ─────────────────────────────

    function renderDiscountTable(tableId, before, after, hasInput) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        tbody.innerHTML = "";

        const gmvBefore = before.gmv_fp || 1;
        const gmvAfter = after ? after.gmv_fp || 1 : gmvBefore;

        const rows = [];
        DISCOUNT_CATEGORIES.forEach((c) => {
            const valB = before[c.key] || 0;
            const pctB = valB / gmvBefore;
            const valA = after ? after[c.key] || 0 : valB;
            const pctA = after ? valA / gmvAfter : pctB;
            rows.push({ label: c.label, pctB, pctA });
        });

        rows.push({
            label: "Comissão",
            pctB: before.pct_comissao || 0,
            pctA: after ? after.pct_comissao || 0 : before.pct_comissao || 0,
            isComissao: true,
        });

        const totalPctB = (before.vlr_total || 0) / gmvBefore;
        const totalPctA = after ? (after.vlr_total || 0) / gmvAfter : totalPctB;

        rows.forEach((r) => {
            const tr = document.createElement("tr");
            const delta = r.pctA - r.pctB;
            let deltaClass = "delta-zero";
            let deltaStr = "-";
            if (hasInput && Math.abs(delta) > 0.000001) {
                deltaClass = delta > 0 ? (r.isComissao ? "delta-zero" : "delta-pos") : "delta-neg";
                deltaStr = (delta > 0 ? "+" : "") + (delta * 100).toFixed(4) + "%";
            }
            tr.innerHTML = `
                <td>${r.label}</td>
                <td>${fmt(r.pctB, "pct")}</td>
                <td class="col-sim">${hasInput ? fmt(r.pctA, "pct") : "-"}</td>
                <td class="${deltaClass}">${deltaStr}</td>
            `;
            tbody.appendChild(tr);
        });

        const trTotal = document.createElement("tr");
        trTotal.className = "row-total";
        const totalDelta = totalPctA - totalPctB;
        let totalDeltaClass = "delta-zero";
        let totalDeltaStr = "-";
        if (hasInput && Math.abs(totalDelta) > 0.000001) {
            totalDeltaClass = totalDelta > 0 ? "delta-pos" : "delta-neg";
            totalDeltaStr = (totalDelta > 0 ? "+" : "") + (totalDelta * 100).toFixed(4) + "%";
        }
        trTotal.innerHTML = `
            <td>TOTAL</td>
            <td>${fmt(totalPctB, "pct")}</td>
            <td class="col-sim">${hasInput ? fmt(totalPctA, "pct") : "-"}</td>
            <td class="${totalDeltaClass}">${totalDeltaStr}</td>
        `;
        tbody.appendChild(trTotal);
    }

    // ─── Limit bars ────────────────────────────────────────

    function renderLimitBar(prefix, currentPct, simPct, hasInput) {
        const barAtual = document.getElementById(`bar${prefix}Atual`);
        const barSim = document.getElementById(`bar${prefix}Sim`);
        const lblAtual = document.getElementById(`lim${prefix}Atual`);
        const lblSim = document.getElementById(`lim${prefix}Sim`);
        const lblMargem = document.getElementById(`lim${prefix}Margem`);

        const maxDisplay = LIMIT_PCT;
        const pctWidth = (v) => Math.min((v / maxDisplay) * 100, 105) + "%";

        barAtual.style.width = pctWidth(currentPct);
        barAtual.className = "limit-bar-fill";
        if (currentPct > LIMIT_PCT) barAtual.classList.add("danger");
        else if (currentPct > 0.03) barAtual.classList.add("warn");

        if (hasInput && simPct > currentPct) {
            barSim.style.width = pctWidth(simPct);
            barSim.style.left = pctWidth(currentPct);
            const simWidth = ((simPct - currentPct) / maxDisplay) * 100;
            barSim.style.width = Math.min(simWidth, 105 - (currentPct / maxDisplay) * 100) + "%";
            barSim.className = "limit-bar-fill sim";
            if (simPct > LIMIT_PCT) barSim.classList.add("danger");
            else if (simPct > 0.03) barSim.classList.add("warn");
        } else {
            barSim.style.width = "0%";
        }

        lblAtual.textContent = fmt(currentPct, "pct");
        lblSim.textContent = hasInput ? fmt(simPct, "pct") : "-";

        const margem = LIMIT_PCT - (hasInput ? simPct : currentPct);
        lblMargem.textContent = fmt(margem, "pct");
        lblMargem.style.color = margem < 0 ? "var(--red)" : margem < 0.005 ? "var(--yellow)" : "var(--green)";
    }

    // ─── Trend cards ───────────────────────────────────────

    function colorClass(pct) {
        if (pct == null) return "";
        if (pct >= 1) return "good";
        if (pct >= 0.8) return "warn";
        return "bad";
    }

    function renderTrends(trend, gmvPedido, hasInput) {
        const el = (id) => document.getElementById(id);

        // Daily
        el("tdMetaDia").textContent = fmt(trend.meta_prover_dia, "brl");
        el("tdRealizadoHoje").textContent = fmt(trend.realizado_hoje, "brl");

        const atingDia = trend.meta_prover_dia ? trend.realizado_hoje / trend.meta_prover_dia : 0;
        el("tdAtingAtual").textContent = fmt(atingDia, "pct");
        el("tdAtingAtual").className = "trend-value " + colorClass(atingDia);

        const pctDiaDecorrido = trend.percentual_dia_decorrido || 0;
        const trendFechDia = trend.trend_fechamento_dia || trend.realizado_hoje;
        const trendDiaAtual = trend.meta_prover_dia ? trendFechDia / trend.meta_prover_dia : 0;
        el("tdTrendAtual").textContent = fmt(trendDiaAtual, "pct");
        el("tdTrendAtual").className = "trend-value " + colorClass(trendDiaAtual);

        if (hasInput) {
            const newRealizadoHoje = trend.realizado_hoje + gmvPedido;
            const atingDiaSim = trend.meta_prover_dia ? newRealizadoHoje / trend.meta_prover_dia : 0;
            el("tdAtingSim").textContent = fmt(atingDiaSim, "pct");
            el("tdAtingSim").className = "trend-value " + colorClass(atingDiaSim);

            const realizadoFechado = trend.realizado_horas_fechadas || trend.realizado_hoje;
            const newFechado = realizadoFechado + gmvPedido;
            const trendFechSim = pctDiaDecorrido >= 0.05 ? newFechado / pctDiaDecorrido : newFechado;
            const trendDiaSim = trend.meta_prover_dia ? trendFechSim / trend.meta_prover_dia : 0;
            el("tdTrendSim").textContent = fmt(trendDiaSim, "pct");
            el("tdTrendSim").className = "trend-value " + colorClass(trendDiaSim);
        } else {
            el("tdAtingSim").textContent = "-";
            el("tdAtingSim").className = "trend-value";
            el("tdTrendSim").textContent = "-";
            el("tdTrendSim").className = "trend-value";
        }

        // Monthly
        el("tmMetaMes").textContent = fmt(trend.meta_mensal, "brl");
        el("tmRealizadoMtd").textContent = fmt(trend.realizado_mtd, "brl");
        el("tmAtingAtual").textContent = fmt(trend.atingimento_mensal, "pct");
        el("tmAtingAtual").className = "trend-value " + colorClass(trend.atingimento_mensal);

        const trendFator = trend.pesos_passados ? trend.total_pesos_mes / trend.pesos_passados : 1;
        el("tmTrendAtual").textContent = fmt(trend.trend_meta_mensal, "pct");
        el("tmTrendAtual").className = "trend-value " + colorClass(trend.trend_meta_mensal);

        if (hasInput) {
            const newMtd = trend.realizado_mtd + gmvPedido;
            const atingMensalSim = trend.meta_mensal ? newMtd / trend.meta_mensal : 0;
            el("tmAtingSim").textContent = fmt(atingMensalSim, "pct");
            el("tmAtingSim").className = "trend-value " + colorClass(atingMensalSim);

            const trendMensalSim = newMtd * trendFator;
            const trendMetaSim = trend.meta_mensal ? trendMensalSim / trend.meta_mensal : 0;
            el("tmTrendSim").textContent = fmt(trendMetaSim, "pct");
            el("tmTrendSim").className = "trend-value " + colorClass(trendMetaSim);
        } else {
            el("tmAtingSim").textContent = "-";
            el("tmAtingSim").className = "trend-value";
            el("tmTrendSim").textContent = "-";
            el("tmTrendSim").className = "trend-value";
        }
    }

    // ─── Main update ───────────────────────────────────────

    function update() {
        if (!DATA) return;

        const gmvPedido = parseNum(document.getElementById("gmvPedido"));
        const pctInput = parseNum(document.getElementById("pctDesconto"));
        const vlrInput = parseNum(document.getElementById("vlrDesconto"));
        const hasInput = gmvPedido > 0 && (pctInput > 0 || vlrInput > 0);

        let pctDesconto = pctInput / 100;
        let vlrDesconto = vlrInput;

        if (gmvPedido > 0) {
            if (pctInput > 0 && !_vlrFocused) {
                vlrDesconto = gmvPedido * pctDesconto;
                document.getElementById("vlrDesconto").value = vlrDesconto.toFixed(2);
            } else if (vlrInput > 0 && !_pctFocused) {
                pctDesconto = vlrDesconto / gmvPedido;
                document.getElementById("pctDesconto").value = (pctDesconto * 100).toFixed(2);
            }
        }

        const todayRow = getToday(DATA.daily_discounts);
        const monthAgg = aggregateMonth(DATA.daily_discounts);

        const todaySim = hasInput ? simulate(todayRow, gmvPedido, vlrDesconto, pctDesconto) : null;
        const monthSim = hasInput ? simulate(monthAgg, gmvPedido, vlrDesconto, pctDesconto) : null;

        const badge = document.getElementById("discountType");
        if (hasInput) {
            const simMensalPct = monthSim ? monthSim.vlr_total / monthSim.gmv_fp : 0;
            if (simMensalPct <= 0.035) {
                badge.textContent = "Dentro do limite (" + fmt(simMensalPct, "pct") + ")";
                badge.className = "info-badge vendedores";
            } else {
                badge.textContent = "Acima do limite 3.5% (" + fmt(simMensalPct, "pct") + ")";
                badge.className = "info-badge supervisores";
            }
        } else {
            badge.textContent = "Preencha os campos";
            badge.className = "info-badge";
        }

        const todayPct = todayRow.gmv_fp ? (todayRow.vlr_total || 0) / todayRow.gmv_fp : 0;
        const todaySimPct = todaySim ? todaySim.vlr_total / todaySim.gmv_fp : todayPct;
        renderLimitBar("Diario", todayPct, todaySimPct, hasInput);

        const monthPct = monthAgg.gmv_fp ? monthAgg.vlr_total / monthAgg.gmv_fp : 0;
        const monthSimPct = monthSim ? monthSim.vlr_total / monthSim.gmv_fp : monthPct;
        renderLimitBar("Mensal", monthPct, monthSimPct, hasInput);

        renderTrends(DATA.gmv_trend, gmvPedido, hasInput);
    }

    // ─── Input binding ─────────────────────────────────────

    let _pctFocused = false;
    let _vlrFocused = false;

    function bindInputs() {
        const gmvEl = document.getElementById("gmvPedido");
        const pctEl = document.getElementById("pctDesconto");
        const vlrEl = document.getElementById("vlrDesconto");

        pctEl.addEventListener("focus", () => { _pctFocused = true; _vlrFocused = false; });
        vlrEl.addEventListener("focus", () => { _vlrFocused = true; _pctFocused = false; });

        [gmvEl, pctEl, vlrEl].forEach((el) => {
            el.addEventListener("input", update);
        });
    }

    // ─── Refresh ─────────────────────────────────────────────

    function showUpdatedAt() {
        if (!DATA || !DATA.updated_at) return;
        const s = DATA.updated_at;
        const [datePart, rest] = s.split("T");
        const time = rest.split(/[-+]/)[0].split(".")[0];
        const [y, m, d] = datePart.split("-");
        document.getElementById("updatedAt").textContent =
            "Atualizado: " + d + "/" + m + "/" + y + ", " + time;
    }

    async function loadData() {
        const resp = await fetch("/api/data");
        DATA = await resp.json();
        showUpdatedAt();
        update();
    }

    async function doRefresh() {
        const btn = document.getElementById("refreshBtn");
        const label = document.getElementById("refreshLabel");
        btn.disabled = true;
        btn.classList.add("spinning");
        label.textContent = "Atualizando...";

        try {
            const resp = await fetch("/api/refresh", { method: "POST" });
            const result = await resp.json();
            if (result.ok) {
                await loadData();
                label.textContent = "Atualizado!";
                setTimeout(() => { label.textContent = "Atualizar"; }, 2000);
            } else {
                label.textContent = "Erro";
                console.error("Refresh failed:", result.error);
                setTimeout(() => { label.textContent = "Atualizar"; }, 3000);
            }
        } catch (e) {
            label.textContent = "Erro";
            console.error("Refresh error:", e);
            setTimeout(() => { label.textContent = "Atualizar"; }, 3000);
        } finally {
            btn.disabled = false;
            btn.classList.remove("spinning");
        }
    }

    function bindRefreshButton() {
        const btn = document.getElementById("refreshBtn");
        if (btn) btn.addEventListener("click", doRefresh);
    }

    // ─── Init ──────────────────────────────────────────────

    async function init() {
        try {
            await loadData();
        } catch (e) {
            console.error("Failed to load data", e);
            return;
        }

        bindInputs();
        bindRefreshButton();
    }

    document.addEventListener("DOMContentLoaded", init);
})();
