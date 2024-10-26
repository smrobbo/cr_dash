import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import plotly.graph_objects as go
import plotly.express as px
import math

from team import team

st.set_page_config(layout="wide", page_title="CR Sales Dash", page_icon=":bar_chart:")


def run():

    def get_quarter(date):
        if pd.isnull(date):
            return
        quarter = (date.month - 1) // 3 + 1
        year = date.year
        return f"{year} Q{quarter}"

    def week_of_quarter(date):
        if pd.isnull(date):
            return
        quarter_start = date - pd.offsets.QuarterBegin(startingMonth=1)
        return ((date - quarter_start).days // 7) + 1

    today = datetime.now()
    start_of_this_month = datetime(today.year, today.month, 1)
    start_date = start_of_this_month - pd.DateOffset(months=12)
    current_quarter = get_quarter(today)
    current_week_of_quarter = week_of_quarter(today)

    months = pd.date_range(
        start=start_date, end=start_of_this_month + pd.DateOffset(months=1), freq="ME"
    ).map(lambda x: x.replace(day=1))

    df = pd.DataFrame({"start_date": months})
    df["label"] = df['start_date'].map(lambda x: x.strftime("%b %Y"))
    df.set_index("label", inplace=True)

    st.write(f"# CR Sales Dash")
    opps_upload = st.file_uploader("Upload Opportunities", type="xlsx")

    process = None
    opp_df = None
    down_payments = None
    final_payments = None

    if opps_upload is not None:
        process = st.button("Process Data")

    if opps_upload is not None and process:
        # Upload data
        opp_df = pd.read_excel(opps_upload)
        opp_df.columns = [i.replace(" ", "_").lower() for i in opp_df.columns]
        opp_df[
            [
                "created_date",
                "verified_down_payment_date",
                "verified_final_payment_date",
                "close_date",
            ]
        ] = opp_df[
            [
                "created_date",
                "verified_down_payment_date",
                "verified_final_payment_date",
                "close_date",
            ]
        ].map(
            pd.to_datetime
        )
        opp_df["region"] = opp_df.billing_country.map(
            lambda x: "us" if x == "United States" else "intl"
        )
        opp_df = opp_df.sort_values(by='created_date', ascending=True)

        # Calc columns
        opp_df["created_month"] = opp_df.created_date.dt.strftime("%b %Y")

        opp_df["dp_month"] = opp_df.verified_down_payment_date.dt.strftime("%b %Y")
        opp_df["dp_quarter"] = opp_df.verified_down_payment_date.map(get_quarter)
        opp_df["dp_week_of_quarter"] = opp_df.verified_down_payment_date.map(
            week_of_quarter
        )

        opp_df["fp_month"] = opp_df.verified_final_payment_date.dt.strftime("%b %Y")
        opp_df["fp_quarter"] = opp_df.verified_final_payment_date.map(get_quarter)
        opp_df["fp_week_of_quarter"] = opp_df.verified_final_payment_date.map(
            week_of_quarter
        )

        months_in_order = opp_df.groupby('created_month').agg({'created_date': 'min'}).sort_values(by='created_date', ascending=True).index

    ###########
    # RUNRATE #
    ###########

    if opp_df is not None:

        # Down Payments Runrate
        dp_runrate = (
            pd.pivot_table(
                opp_df,
                index="dp_week_of_quarter",
                columns="dp_quarter",
                values="verified_down_payment_amount",
                aggfunc="count",
                fill_value=0,
            )
            .cumsum()
            .iloc[:, -8:] # Last 8 quarters
        )

        # Remove months after current month
        dp_runrate.loc[dp_runrate.index > current_week_of_quarter, current_quarter] = (
            pd.NA
        )

        # Final Payments Run Rate
        fp_runrate = (
            pd.pivot_table(
                opp_df,
                index="fp_week_of_quarter",
                columns="fp_quarter",
                values="verified_final_payment_amount",
                aggfunc="count",
                fill_value=0,
            )
            .cumsum()
            .iloc[:, -8:] # Last 8 quarters
        )

        # Remove months after current month
        fp_runrate.loc[fp_runrate.index > current_week_of_quarter, current_quarter] = (
            pd.NA
        )

        # Create a color scale for quarters and set increasing thickness
        color_scale = alt.Scale(scheme="darkmulti", reverse=True)
        thickness = alt.Scale(range=[2, 8])
        opacity_scale = alt.Scale(range=[0.4, 1])

        st.write("# Run Rate")

        col1, col2 = st.columns(2)

        with col1:

            dp_melted = (
                dp_runrate.reset_index()
                .melt(
                    id_vars="dp_week_of_quarter", var_name="quarter", value_name="value"
                )
                .dropna()
            )

            # Line
            dp_chart = (
                alt.Chart(dp_melted)
                .mark_line()
                .encode(
                    x=alt.X(
                        "dp_week_of_quarter:N",
                        title="Week of Quarter",
                        axis=alt.Axis(labelAngle=0),
                    ),
                    y=alt.Y("value:Q", title=None),
                    color=alt.Color("quarter:N", scale=color_scale, legend=None),
                    size=alt.Size("quarter:N", scale=thickness),
                    opacity=alt.Opacity("quarter:N", scale=opacity_scale),
                    strokeDash=alt.condition(
                        alt.datum.quarter == current_quarter,
                        alt.value([10, 8]),
                        alt.value([1, 0]),
                    ),
                )
                .properties(width=600, height=350)
            )

            # Text
            dp_text = (
                alt.Chart(dp_melted)
                .mark_text(align="left", dx=5, dy=0, fontSize=14)
                .encode(
                    x=alt.X("dp_week_of_quarter:N", aggregate="max"),
                    y=alt.Y("value:Q", aggregate={"argmax": "dp_week_of_quarter"}),
                    text="quarter:N",
                    color=alt.Color("quarter:N", scale=color_scale),
                )
            )

            st.write(f"### Down Payments")
            st.altair_chart((dp_chart + dp_text).configure_legend(disable=True), use_container_width=True)

        with col2:

            fp_melted = (
                fp_runrate.reset_index()
                .melt(
                    id_vars="fp_week_of_quarter", var_name="quarter", value_name="value"
                )
                .dropna()
            )

            # Line
            fp_chart = (
                alt.Chart(fp_melted)
                .mark_line()
                .encode(
                    x=alt.X(
                        "fp_week_of_quarter:N",
                        title="Week of Quarter",
                        axis=alt.Axis(labelAngle=0),
                    ),
                    y=alt.Y("value:Q", title=None),
                    color=alt.Color("quarter:N", scale=color_scale, legend=None),
                    size=alt.Size("quarter:N", scale=thickness),
                    opacity=alt.Opacity("quarter:N", scale=opacity_scale),
                    strokeDash=alt.condition(
                        alt.datum.quarter == current_quarter,
                        alt.value([10, 8]),
                        alt.value([1, 0]),
                    ),
                )
                .properties(width=600, height=350)
            )

            # Text
            fp_text = (
                alt.Chart(fp_melted)
                .mark_text(align="left", dx=5, dy=0, fontSize=14)
                .encode(
                    x=alt.X("fp_week_of_quarter:N", aggregate="max"),
                    y=alt.Y("value:Q", aggregate={"argmax": "fp_week_of_quarter"}),
                    text="quarter:N",
                    color=alt.Color("quarter:N", scale=color_scale),
                )
            )

            st.write(f"### Final Payments")
            st.altair_chart((fp_chart + fp_text).configure_legend(disable=True), use_container_width=True)

    #####################
    # DP PER RAMPED FTE #
    #####################

    if opp_df is not None:

        # Down Payments
        down_payments = opp_df.pivot_table(
            index="dp_month",
            columns="region",
            values="opportunity_name",
            aggfunc="count",
            fill_value=0,
        )
        down_payments["total"] = down_payments.sum(axis=1)
        down_payments = down_payments.reindex(df.index).fillna(0)

        for i, row in df.iterrows():
            # Find all ramped and active employees
            ramped_team = team[
                (team.ramped_date <= row['start_date'])
                & ((team.end_date >= row['start_date']) | (pd.isna(team.end_date)))
            ]
            df.at[i, 'ramped_fte'] = ramped_team.shape[0]

        st.write("# Down Payments Per Ramped FTE Per Month")

        dp_fte = down_payments.join(df[['ramped_fte']]).reset_index()
        dp_fte['dps_per_fte'] = dp_fte['total'] / dp_fte['ramped_fte']
        dp_fte['target'] = 0.5

        fig = go.Figure()

        # DPs per FTE
        fig.add_trace(
            go.Scatter(
                x=dp_fte['label'],
                y=dp_fte['dps_per_fte'],
                fill='tozeroy',
                mode='lines',
                name='Down Payments',
                line=dict(width=5),
            )
        )

        # Target
        fig.add_trace(
            go.Scatter(
                x=dp_fte['label'],
                y=dp_fte['target'],
                fill='tozeroy',
                mode='lines',
                name='Target',
                line=dict(color='maroon', dash='dash', width=3),
                fillcolor='rgba(128, 0, 0, 0.2)'
            )
        )

        # Ramped FTE
        fig.add_trace(
            go.Scatter(
                x=dp_fte['label'],
                y=dp_fte['ramped_fte'],
                mode='lines',
                name='Ramped FTE (RHS)',
                line=dict(color='grey', dash='dash', width=1),
                yaxis='y2'
            )
        )

        fig.update_layout(
            yaxis=dict(
                title="Down Payments",
                titlefont=dict(color="blue"),
                tickfont=dict(color="blue"),
                range=[0, dp_fte['dps_per_fte'].max()],
                dtick=0.5,
                automargin=True,
                constrain='domain',
            ),
            yaxis2=dict(
                title="Ramped FTE",
                titlefont=dict(color="grey"),
                tickfont=dict(color="grey"),
                overlaying="y",
                side="right",
                dtick=1,
                range=[0, dp_fte.ramped_fte.max() + 1],
                automargin=True,
                constrain='domain',
            ),
            xaxis=dict(title="Month"),
            margin=dict(l=0, r=0, t=0, b=0),
            dragmode=False,
            width=600,
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5
            ),
        )

        st.plotly_chart(fig, config={'displayModeBar': False}, use_container_width=True)

    #################
    # TEAM ANALYSIS #
    #################

    if opp_df is not None:

        active_team = team[team.active == True]

        @st.fragment
        def analyze_person():

            stages = opp_df.stage.value_counts().to_frame().sort_values('stage', ascending=True)
            selected_person = st.selectbox("Select Team Member", ['All'] + list(active_team['name']))

            if selected_person == 'All':
                lim_opps = opp_df.copy()
            else:
                lim_opps = opp_df[opp_df.opportunity_owner == selected_person]

            lim_stages = lim_opps.stage.value_counts().to_frame(name=selected_person)
            lim_stages = stages.join(lim_stages).fillna(0).iloc[0:-2]

            # Create clickable link for opportunity_name
            lim_opps['sfdc'] = lim_opps.apply(
                lambda row: f"https://carbonrobotics.lightning.force.com/lightning/r/Opportunity/{row['opportunity_id']}/view",
                axis=1
            )

            selected_opps = lim_opps[lim_opps.stage.isin(lim_stages.index)][[
                'opportunity_name',
                'sfdc',
                'created_date',
                'stage',
                'opportunity_owner',
                'billing_country',
            ]]
            selected_opps['age'] = selected_opps['created_date'].apply(lambda x: (datetime.now() - x).days)
            selected_opps['created_date'] = selected_opps['created_date'].dt.strftime("%b %d, %Y")
            selected_opps = selected_opps.sort_values(by=['stage', 'age'], ascending=[True, False])

            col1, col2 = st.columns([2,3])

            with col1:
                st.write(f"### Funnel ({selected_person})")
                fig = go.Figure(go.Funnel(
                    y=lim_stages.index,
                    x=lim_stages[selected_person],
                    textinfo="value+percent total"
                ))
                st.plotly_chart(fig)

            with col2:
                st.write(f"### Active Opportunities ({selected_opps.shape[0]})")
                styled_df = selected_opps.style.background_gradient(subset=['age'], cmap='RdYlGn_r')
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    column_config={
                        "sfdc": st.column_config.LinkColumn(display_text="go")
                    },
                    hide_index=True,
                )

            opp_seasons = lim_opps.groupby('created_month').size().to_frame(name='Opportunities Created')
            dp_seasons = lim_opps.groupby('dp_month').size().to_frame(name='Down Payments')
            fp_seasons = lim_opps.groupby('fp_month').size().to_frame(name='Final Payments')
            seasons = opp_seasons.join(dp_seasons).join(fp_seasons).reindex(months_in_order).T.fillna(0).astype(int).iloc[:, -18:]
            styled_seasons = seasons.style.background_gradient(cmap='Greens', axis=1)

            st.write("### Seasonality")
            st.dataframe(styled_seasons, use_container_width=True)

            return

        st.write("# Team Analysis")
        analyze_person()

if __name__ == "__main__":
    run()
