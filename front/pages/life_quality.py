import pandas as pd
import streamlit as st
from numpy.random import default_rng as rng

df = pd.read_csv(r"C:\Users\Utilisateur\Desktop\ProjetCertif\ProjetCertif\DATA\processed\life_quality.csv")
df = df.drop(columns = ["Classement"])

st.title("Indices de qualité de vie")

st.dataframe(df.style.highlight_max(axis=0), width="stretch")