import pandas as pd
import numpy as np
import ast
from fastapi import FastAPI, Query, HTTPException
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.ensemble import BaggingRegressor
from pydantic import BaseModel
from enum import Enum
import pickle

# Indicamos la API
app = FastAPI(title='PI MLOps - Micaela Paz DTS13')

#Cargamos el data set
rows = []
with open('steam_games.json') as f: 
    for line in f.readlines():
        rows.append(ast.literal_eval(line)) 
df = pd.DataFrame(rows) 
df['release_date'] = pd.to_datetime(df['release_date'], errors='coerce')
df['metascore'] = pd.to_numeric(df['metascore'], errors='coerce')


# Endpoint 1: Géneros más repetidos por año
@app.get('/Genero')
def genero(año: str):
    # Filtro por el año proporcionado
    df_filtrado = df[df['release_date'].dt.year == int(año)]
    
    # Lista con todos los géneros para el año dado
    generos_list = df_filtrado['genres'].explode().tolist()

    # Conteo de cada género en la lista
    generos_count = pd.Series(generos_list).value_counts()

    # Verifica si hay suficientes datos para ese año
    if generos_count.empty:
        return {"Sin registros para ese año, ingresa otro valor"}
    
    # Obtener los 5 géneros más vendidos en orden correspondiente
    generos_mas_repetidos = generos_count.nlargest(5).to_dict()

    return generos_mas_repetidos

# Endpoint 2: Juegos lanzados en un año
@app.get('/Juegos')
def juegos(año: str):
    # Filtrar los datos por el año especificado
    df_filtrado = df[df['release_date'].dt.year == int(año)]

    # Obtener la lista de juegos lanzados en el año
    juegos_lanzados = df_filtrado['title'].tolist()

    # Verificar si hay suficientes datos para ese año
    if not juegos_lanzados:
        return {"Sin registros para ese año, ingresa otro valor"}

    # Devolver la lista de juegos en un diccionario con el año como clave
    juegos_por_año = {año: juegos_lanzados}

    return juegos_por_año

# Endpoint 3: Specs más comunes por año
@app.get('/Specs')
def specs(año: str):
    # Filtrar el DataFrame por el año proporcionado
    df_filtrado = df[df['release_date'].dt.year == int(año)]

    # Obtener una lista con todos los Specs para el año dado
    specs_list = df_filtrado['specs'].explode().tolist()

    # Calcular el conteo de cada Spec en la lista
    specs_count = pd.Series(specs_list).value_counts()

    # Obtener los 5 Specs más comunes en orden correspondiente
    top_5_specs = specs_count.nlargest(5).to_dict()

    # Verificar si hay suficientes datos para ese año
    if not top_5_specs:
        return {}

    return top_5_specs

# Endpoint 4: Cantidad de juegos con early access en un año
@app.get('/Earlyaccess')
def earlyaccess(año: str):
    # Filtrar los datos por el año especificado y por juegos con early access
    df_filtrado = df[(df['release_date'].dt.year == int(año)) & (df['early_access'] == True)]

    # Contar la cantidad de juegos con early access en el año especificado
    cantidad_juegos_early_access = len(df_filtrado)

    # Crear el diccionario de respuesta
    respuesta = {
        año: cantidad_juegos_early_access
    }

    return respuesta

# Endpoint 5: Análisis de sentimiento por año
@app.get('/Sentiment')
def sentiment(año: str):
    # Filtrar los datos por el año especificado
    df_filtrado = df[df['release_date'].dt.year == int(año)]

    # Contar la cantidad de registros que cumplen con cada análisis de sentimiento
    sentimient_counts = df_filtrado['sentiment'].value_counts()

    # Convertir la serie de conteo en un diccionario
    sentimient_dict = sentimient_counts.to_dict()

    # Eliminar sentimientos que no están en la lista mencionada
    sentimient_valid = ["Mixed", "Positive", "Very Positive", "Mostly Positive",
                            "Negative", "Very Negative", "Mostly Negative", "Overwhelmingly Positive", "Overwhelmingly Negative"]
    sentimient_dict = {sentimient: count for sentimient, count in sentimient_dict.items() if sentimient in sentimient_valid}

    # Verificar si el diccionario está vacío
    if not sentimient_dict:
        return  {"Sin registros para ese año, ingresa otro valor"}

    return sentimient_dict

# Endpoint 6: Top 5 juegos con mayor metascore por año
@app.get('/Metascore')
def metascore(año: str):
    # Filtrar los datos por el año especificado y ordenar por metascore de forma descendente
    df_filtrado = df[df['release_date'].dt.year == int(año)].sort_values(by='metascore', ascending=False)

    # Seleccionar los 5 juegos con mayor metascore y obtener su información de título y metascore
    top_juegos_metascore = df_filtrado.head(5)[['title', 'metascore']].to_dict(orient='records')

    return top_juegos_metascore

# Cargar el modelo de Bagging desde el archivo con pickle
modelo_guardado = "modelo_bagging.pkl"
with open(modelo_guardado, "rb") as file:
    bagging_model = pickle.load(file)

# Definir el Enum para los géneros disponibles
class Genre(str, Enum):
    Action = "Action"
    Adventure = "Adventure"
    Casual = "Casual"
    Early_Access = "Early Access"
    Free_to_Play = "Free to Play"
    Indie = "Indie"
    Massively_Multiplayer = "Massively Multiplayer"
    RPG = "RPG"
    Racing = "Racing"
    Simulation = "Simulation"
    Sports = "Sports"
    Strategy = "Strategy"
    Video_Production = "Video Production"
   

# Cargar el DataFrame df2 con tus datos
df2 = pd.read_csv('df2.csv')

# Definir X_train como las características utilizadas para entrenar el modelo
X_train = df2[["metascore", "year"] + df2.filter(like="genres_").columns.tolist()]
y_train = df2["price"]

# Función para realizar la predicción
def predict_price(metascore, year, genres):
    # Convertir la entrada a un DataFrame
    data = pd.DataFrame([[metascore, year, ",".join(genres)]], columns=["metascore", "year", "genres"])

    # Obtener las variables dummy de los géneros de la misma manera que se hizo durante el entrenamiento
    data_genres = data["genres"].str.get_dummies(sep=",")
    
    # Verificar si hay columnas faltantes en data_genres en comparación con X_train
    missing_columns = set(X_train.columns) - set(data_genres.columns)
    for column in missing_columns:
        data_genres[column] = 0

    # Asegurar el orden de las columnas en data_genres
    data_genres = data_genres[X_train.filter(like="genres_").columns]

    # Concatenar las variables dummy con el resto de las columnas
    data = pd.concat([data[["metascore", "year"]], data_genres], axis=1)

    # Realizar la predicción con el modelo de Bagging
    predicted_price = bagging_model.predict(data)[0]

    # Calcular el RMSE durante el entrenamiento del modelo
    y_pred_train = bagging_model.predict(X_train)
    rmse_train = mean_squared_error(y_train, y_pred_train, squared=False)

    return round(predicted_price, 2), round(rmse_train, 2)  # Redondear a dos decimales

# Definir el modelo de datos para la salida de la predicción
class PredictionOutput(BaseModel):
    predicted_price: float
    rmse: float

# Ruta para la predicción
@app.get("/predict/", response_model=PredictionOutput)
def predict(metascore: float, year: int, genres: Genre = None):
    # Obtener la predicción y el RMSE
    predicted_price, rmse_train = predict_price(metascore, year, genres.value)  # genres.value obtiene el valor del Enum

    # Crear un diccionario con el resultado
    result = {
        "predicted_price": predicted_price,
        "rmse": rmse_train
    }

    return result