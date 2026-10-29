"""Person B - Streamlit frontend for the Subscription Tracker API.

Run:  streamlit run app.py   (API_BASE_URL defaults to http://127.0.0.1:8002)
"""
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from services.cost_calculator import advance_renewal
from ui_common import resolve_api_base_url, api_delete, api_get, api_post, api_put, money

st.set_page_config(page_title="Subscription Tracker (B)", layout="wide")


API_BASE_URL = resolve_api_base_url(st.secrets)
CATEGORY_COLORS = {
    "Streaming": "#ef4444", "Music": "#10b981", "Software": "#3b82f6",
    "Fitness": "#f97316", "News": "#eab308", "Education": "#8b5cf6",
    "Cloud": "#06b6d4", "Gaming": "#ec4899", "Other": "#94a3b8",
}

st.title("Subscription Renewal & Cost Tracker")
st.caption("Person B - Shravan N A (23MID0445) | CSI3007 Advanced Python Programming | "
           f"API: `{API_BASE_URL}`")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Manage Subscriptions", "Upcoming Renewals", "Categories & Tags", "Integration Export"],
)

FREQUENCIES = ["weekly", "monthly", "quarterly", "yearly"]

# ------------------------------------------------------------------ Dashboard
if page == "Dashboard":
    st.subheader("What am I paying for?")
    this_month = date.today().strftime("%Y-%m")
    ok, totals = api_get(API_BASE_URL, "/total", params={"month": this_month})
    if not ok:
        st.error(totals)
    else:
        col1, col2, col3, col4 = st.columns(4)
        if totals["currencies"]:
            monthly = totals["currencies"][0]["monthly_total"]
            yearly = totals["currencies"][0]["yearly_total"]
            cur = totals["currencies"][0]["currency"]
            col1.metric(f"Monthly total ({cur})", money(monthly, cur))
            col2.metric(f"Yearly total ({cur})", money(yearly, cur))
        col3.metric("Active / Inactive", f"{totals['active_count']} / {totals['inactive_count']}")
        due_totals = totals.get("due_in_month_totals") or []
        due_inr = next((d for d in due_totals if d["currency"] == "INR"), None)
        col4.metric(f"Charges due in {this_month}", money(due_inr["total"]) if due_inr else money(0),
                    f"{due_inr['count'] if due_inr else 0} renewals", delta_color="off")
        if len(totals["currencies"]) > 1:
            st.caption("Totals are kept per currency; only the first currency is shown above.")

        if totals["by_category"]:
            df = pd.DataFrame(totals["by_category"]).rename(columns={"monthly_total": "Monthly (INR)"})
            fig = px.pie(
                df, names="category", values="Monthly (INR)", hole=0.4,
                title="Monthly spend by category", color="category",
                color_discrete_map=CATEGORY_COLORS,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True, hide_index=True)

        ok, renewals = api_get(API_BASE_URL, "/renewals", params={"days": 7})
        if not ok:
            st.warning(f"Could not load upcoming renewals: {renewals}")
        elif renewals:
            st.subheader("Renewing in the next 7 days")
            st.dataframe(
                pd.DataFrame(renewals)[["name", "next_renewal_date", "days_until_renewal", "urgency", "monthly_cost"]],
                use_container_width=True, hide_index=True,
            )

# --------------------------------------------------------- Manage Subscriptions
elif page == "Manage Subscriptions":
    st.subheader("All subscriptions")
    show_all = st.toggle("Include inactive", value=True)
    ok, subs = api_get(API_BASE_URL, "/subscriptions", params={"limit": 500})
    if not ok:
        st.error(subs)
    else:
        if not show_all:
            subs = [s for s in subs if s["active"]]
        if subs:
            df = pd.DataFrame(subs)[
                ["id", "name", "category", "plan", "amount", "billing_frequency",
                 "next_renewal_date", "monthly_cost", "active"]
            ]
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown("#### Quick actions")
            col1, col2, col3 = st.columns(3)
            sub_id = col1.number_input("Subscription ID", min_value=1, step=1)
            target = next((s for s in subs if s["id"] == int(sub_id)), None)
            if target is None:
                st.info("Enter a valid subscription ID to enable actions.")
            else:
                col2.write(f"Selected: **{target['name']}** ({target['billing_frequency']})")
                if col2.button("Mark renewed now"):
                    next_date = advance_renewal(date.today(), target["billing_frequency"])
                    ok, result = api_put(
                        API_BASE_URL, f"/subscriptions/{int(sub_id)}",
                        {"next_renewal_date": next_date.isoformat()},
                    )
                    if ok:
                        st.success(f"{target['name']} next renewal -> {next_date}")
                        st.rerun()
                    else:
                        st.error(result)
                new_active = col3.toggle("Active", value=target["active"], key="toggle_active")
                if new_active != target["active"]:
                    ok, result = api_put(
                        API_BASE_URL, f"/subscriptions/{int(sub_id)}", {"active": new_active}
                    )
                    if ok:
                        st.success("Subscription state updated.")
                        st.rerun()
                    else:
                        st.error(result)
                if col3.button("Delete subscription"):
                    ok, result = api_delete(API_BASE_URL, f"/subscriptions/{int(sub_id)}")
                    if ok:
                        st.success(f"Deleted #{int(sub_id)}")
                        st.rerun()
                    else:
                        st.error(result)
        else:
            st.info("No subscriptions recorded yet.")

    st.markdown("#### Add a subscription")
    with st.form("add_subscription", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name = c1.text_input("Name *", placeholder="Netflix")
        category = c2.selectbox(
            "Category *", ["Streaming", "Music", "Software", "Fitness", "News", "Education", "Cloud", "Gaming", "Other"]
        )
        plan = c1.text_input("Plan", placeholder="Premium 4K")
        amount = c2.number_input("Amount per period (INR) *", min_value=0.01, value=199.0, step=10.0)
        c3, c4 = st.columns(2)
        frequency = c3.selectbox("Billing frequency *", FREQUENCIES)
        next_renewal = c3.date_input("Next renewal date *", value=date.today())
        payment = c4.text_input("Payment method", placeholder="UPI Autopay")
        tags_raw = c4.text_input("Tags (comma-separated)", placeholder="family,ott")
        notes = st.text_input("Notes")
        if st.form_submit_button("Save subscription"):
            if not name:
                st.error("Name is required.")
            else:
                body = {
                    "name": name, "category": category, "plan": plan, "amount": amount,
                    "currency": "INR", "billing_frequency": frequency,
                    "next_renewal_date": next_renewal.isoformat(),
                    "payment_method": payment,
                    "tags": [t.strip() for t in tags_raw.split(",") if t.strip()],
                    "notes": notes,
                }
                ok, result = api_post(API_BASE_URL, "/subscriptions", body)
                if ok:
                    st.success(f"Saved #{result['id']} - normalized monthly cost: {money(result['monthly_cost'])}")
                    st.rerun()
                else:
                    st.error(result)

# ------------------------------------------------------------ Upcoming Renewals
elif page == "Upcoming Renewals":
    st.subheader("Renewal forecast")
    days = st.slider("Look-ahead window (days)", 7, 365, 30)
    include_overdue = st.toggle("Include overdue", value=True)
    ok, renewals = api_get(API_BASE_URL, "/renewals", params={"days": days, "include_overdue": include_overdue})
    if not ok:
        st.error(renewals)
    elif renewals:
        df = pd.DataFrame(renewals)[
            ["name", "category", "next_renewal_date", "days_until_renewal", "urgency", "amount", "billing_frequency", "monthly_cost"]
        ]
        st.dataframe(df, use_container_width=True, hide_index=True)
        projected = round(sum(r["amount"] for r in renewals), 2)
        st.metric(f"Sum of bills falling due within {days} days", money(projected))
    else:
        st.info("Nothing renews in this window.")

# ---------------------------------------------------------- Categories & Tags
elif page == "Categories & Tags":
    st.subheader("Explore by category")
    ok, totals = api_get(API_BASE_URL, "/total")
    if ok and totals["by_category"]:
        cat_names = [row["category"] for row in totals["by_category"]]
        chosen = st.selectbox("Category", cat_names)
        ok, detail = api_get(API_BASE_URL, f"/category/{chosen}")
        if ok:
            st.metric(f"Monthly cost of {detail['category']}", money(detail["monthly_total"]))
            st.metric("Subscriptions", detail["count"])
            if detail["subscriptions"]:
                st.dataframe(pd.DataFrame(detail["subscriptions"]), use_container_width=True, hide_index=True)
    elif ok:
        st.info("No active subscriptions yet.")

    st.subheader("All tags")
    ok, tags = api_get(API_BASE_URL, "/tags")
    if ok:
        if tags:
            st.dataframe(pd.DataFrame(tags), use_container_width=True, hide_index=True)
        else:
            st.info("No tags yet.")

# --------------------------------------------------------- Integration Export
elif page == "Integration Export":
    st.subheader("GET /integration/export - the contract Person A consumes")
    st.caption("Stable JSON: stable external_ref per subscription, pre-normalized monthly_cost, "
               "active flag included. A imports over HTTP - never via this app's database file.")
    ok, payload = api_get(API_BASE_URL, "/integration/export")
    if ok:
        st.metric("Subscriptions in export", payload["count"])
        st.caption(f"service={payload['service']} | contract_version={payload['contract_version']}")
        st.json(payload)
    else:
        st.error(payload)
