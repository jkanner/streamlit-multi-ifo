import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import requests, os
from gwpy.timeseries import TimeSeries, TimeSeriesDict
from gwosc.locate import get_urls
from gwosc import datasets
from gwosc.api import fetch_event_json

from copy import deepcopy
import base64

# -- Default detector list
detectorlist = ['H1','L1', 'V1']

# Title the app
st.title('Gravitational Wave Quickview App')

st.markdown("""
 * Use the menu at left to select data and set plot parameters
 * Learn more at https://gw-openscience.org
""")

@st.cache   #-- Magic command to cache data
def load_gw(t0, detectorlist):
    straindict = {}
    for ifo in detectorlist:
        straindict[ifo] = TimeSeries.fetch_open_data(ifo, t0-14, t0+14, cache=False)
    return straindict

st.sidebar.markdown("## Select Data Time and Detector")

# -- Get list of events
# find_datasets(catalog='GWTC-1-confident',type='events')
eventlist = datasets.find_datasets(type='events')
eventlist = [name.split('-')[0] for name in eventlist if name[0:2] == 'GW']
eventset = set([name for name in eventlist])
eventlist = list(eventset)
eventlist.sort()

chosen_event = st.sidebar.selectbox('Select Event', eventlist)
t0 = datasets.event_gps(chosen_event)
detectorlist = list(datasets.event_detectors(chosen_event))
detectorlist.sort()
st.subheader(chosen_event)

# -- Experiment to display masses
try:
    jsoninfo = fetch_event_json(chosen_event)
    for name, nameinfo in jsoninfo['events'].items():        
        st.write('Mass 1:', nameinfo['mass_1_source'], 'M$_{\odot}$')
        st.write('Mass 2:', nameinfo['mass_2_source'], 'M$_{\odot}$')
        #st.write('Distance:', int(nameinfo['luminosity_distance']), 'Mpc')
        st.write('Network SNR:', int(nameinfo['network_matched_filter_snr']))
        eventurl = 'https://gw-osc.org/eventapi/html/event/{}'.format(chosen_event)
        st.markdown('Event page: {}'.format(eventurl))
        st.write('\n')
except:
    pass


    
#-- Choose detector as H1, L1, or V1
# detector = st.sidebar.selectbox('Detector', detectorlist)

# -- Create sidebar for plot controls
st.sidebar.markdown('## Set Plot Parameters')
dtboth = st.sidebar.slider('Time Range (seconds)', 0.1, 2.0, 0.2)  # min, max, default
dt = dtboth / 2.0

st.sidebar.markdown('#### Whitened and band-passed data')
whiten = st.sidebar.checkbox('Whiten?', value=True)
freqrange = st.sidebar.slider('Band-pass frequency range (Hz)', min_value=10, max_value=2000, value=(30,400))


#-- Create a text element and let the reader know the data is loading.
strain_load_state = st.text('Loading data...this may take a minute')
try:
    straindict_temp = load_gw(t0, detectorlist)
    straindict = deepcopy(straindict_temp)
except:
    st.text('Data load failed.  Try a different time and detector pair.')
    st.text('Problems can be reported to gwosc@igwn.org')
    raise st.ScriptRunner.StopException
    
strain_load_state.text('Loading data...done!')

#-- Make a time series plot

cropstart = t0 - dt
cropend   = t0 + dt


cleandict = TimeSeriesDict()
paramdict = {}
st.subheader('Whitened and Band-passed Data')
for ifo, strain in straindict.items():
    
    # -- Try whitened and band-passed plot
    # -- Whiten and bandpass data    
    if whiten:
        white_data = strain.whiten()
        bp_data = white_data.bandpass(freqrange[0], freqrange[1])
    else:
        bp_data = strain.bandpass(freqrange[0], freqrange[1])

    
    # fig3 = bp_cropped.plot()
    # st.pyplot(fig3, clear_figure=True)

    paramdict[ifo] = {}
    paramdict[ifo]['offset'] = st.sidebar.slider('{} time offset (ms)'.format(ifo), value=0.0,
                                                 min_value = -20.0,
                                                 max_value = 20.0,
                                                 step = 0.1,
                                                 )
    paramdict[ifo]['invert'] = st.sidebar.checkbox('Apply minus sign to {}?'.format(ifo), value=False)

    # -- Apply time shift and minus signs
    shift = paramdict[ifo]['offset']*0.001
    bp_data.shift(shift)
    if paramdict[ifo]['invert']: bp_data = -1.0*bp_data

    bp_cropped = bp_data.crop(cropstart, cropend)
    cleandict[ifo] = bp_cropped
    

#-- Make a better plot with all the clean data
plot = cleandict.plot()
plot.gca().legend()
st.pyplot(plot)
    
# -- Allow data download

for ifo, strain in cleandict.items():
    download={}
    download['Time']=strain.times
    download[ifo]=strain.value
    df = pd.DataFrame(download)
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a href="data:file/csv;base64,{b64}">Download Data as CSV File</a>'
    st.markdown(ifo + ': ' + href, unsafe_allow_html=True)



st.subheader("About this app")
st.markdown("""
This app displays data from LIGO, Virgo, and GEO downloaded from
the Gravitational Wave Open Science Center at https://gw-openscience.org .


You can see how this works in the [Quickview Jupyter Notebook](https://github.com/losc-tutorial/quickview)

""")
