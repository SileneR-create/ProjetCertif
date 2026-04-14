import pandas as pd
import streamlit as st
from numpy.random import default_rng as rng

st.title('Destinations')

df = pd.read_csv(r"C:\Users\Utilisateur\Desktop\ProjetCertif\ProjetCertif\DATA\processed\destinations.csv")
st.map(df)