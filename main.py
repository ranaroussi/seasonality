import altair as alt
import yfinance as yf
import streamlit as st
import pandas as pd

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


@st.cache(allow_output_mutation=True)
def run(ticker):
    data = yf.download(ticker, period='max', show_errors=False, progress=False)
    if data.empty:
        return {
            "error": True
        }

    df = pd.DataFrame({
        'return': yf.download(ticker, period='max', show_errors=False, progress=False)['Close'].pct_change().fillna(0)
    })
    # use full years only
    df = df[df.index >= df[df.index.month == 1].index[0]]
    df = df[df.index <= df[df.index.month == 12].index[-1]]

    # chart
    seasonal = {}
    for year in df.index.year.unique():
        seasonal[year] = df[df.index.year == year].reset_index()['return']
    seasonal = pd.DataFrame(seasonal)

    # old way (annual cumsum)
    # seasonal_returns = 100 * seasonal.dropna(how='all').mean(axis=1).cumsum()

    # monthly cumsum
    longest_year = seasonal[-1:].T.dropna().index[0]
    seasonal.index = df[df.index.year == longest_year].index.strftime('%Y%m')
    seasonal_returns = seasonal.dropna(how='all').groupby(seasonal.index).cumsum()
    seasonal_returns.reset_index(drop=True, inplace=True)
    seasonal_returns = seasonal_returns.dropna(how='all').mean(axis=1)

    expr = ''
    for idx, val in enumerate(range(0, len(seasonal), 22)):
      expr += f"datum.label == {val} ? '{months[idx]}' : "
    expr += 'null'

    source = pd.DataFrame({
      'day': seasonal_returns.index,
      'returns': seasonal_returns.values
    })

    chart = (
        alt.Chart(source)
        .mark_line()
        .encode(
          x=alt.X(
            'day',
              title="Trading Day #",
              axis=alt.Axis(
              tickCount=df.shape[0],
              grid=False,
              labelExpr = expr,
            )
          ),
          y=alt.Y(
            'returns',
            title="Return %",
            scale=alt.Scale(domain=[seasonal_returns.min(), seasonal_returns.max()]),
            axis=alt.Axis(format='%')
            # labelExpr="format(datum.value, '~s') +'%'",
          )
        )
    )

    line = alt.Chart(pd.DataFrame({'returns': [0]})).mark_rule().encode(y='returns')

    # data
    monthly = {}
    for year in df.index.year.unique():
        yeardf = df[df.index.year == year]
        monthly[year] = yeardf.groupby(yeardf.index.month).sum() * 100

    data = pd.concat(monthly, axis=1)
    data.columns = [col[0] for col in data.columns]
    data.index = months

    summary = pd.DataFrame(data.mean(axis=1))
    summary.columns = ['Return %']

    info = yf.Ticker(ticker).info

    return {
        "error": False,
        "title": f'{info.get("shortName", ticker)} Seasonal chart',
        "meta": f"{ticker} / {data.columns[0]} - {data.columns[-1]} ({len(data.columns)} years)",
        "chart": chart + line,
        "summary": summary.T,
        "data": data[data.columns[::-1]]
    }



st.set_page_config(page_title="Seasonal stock charts", page_icon='https://img.icons8.com/fluency/48/null/stocks-growth.png')

st.title("Seasonality stock charting")
st.markdown("""A little app that charts the seasonal returns of a stock or ETF. 

- Written by [Ran Aroussi](https://tradologics.com) ([@aroussi](https://twitter.com/ranaroussi)) / [source](https://github.com/ranaroussi/seasonality)
- Tools used: [yfinance](https://github.com/ranaroussi/yfinance), [Pandas](https://pandas.pydata.org/), [Altair](https://altair-viz.github.io/), and [Streamlit](https://streamlit.io/)
""")

st.write("NOT A FINCNCIAL ADVICE. USE AT YOUR OWN RISK.")
st.markdown("""---""")

ticker = st.text_input('Enter the asset ticker (Yahoo! Finance format)', '^GSPC')

if not ticker:
    st.error("Please select an asset.")
else:
    try:
        data = run(ticker)
    except:
        data = { "error": True}

    # data = run(ticker)
    # print(data)

    if data.get('error', True):
        st.error(f"Cannot find asset with ticker `{ticker}`. Asset may be delisted.")

    else:

        st.markdown("""---""")
        st.subheader(data['title'])
        st.write(data['meta'])

        st.altair_chart(data['chart'], use_container_width=True)

        st.markdown("**Monthly average**")
        st.dataframe(data['summary'], use_container_width=True)

        st.markdown("**Raw returns**")
        st.dataframe(data['data'], use_container_width=True)
