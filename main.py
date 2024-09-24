from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import os
import tempfile
import asyncio
import uvicorn
from functools import lru_cache
import functools

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def hello():
    return "Hello"

def add_data_to_json(new_data, file_path='database/user_db.json'):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                existing_data = json.load(file)
        else:
            existing_data = []
        existing_data.append(new_data)
        with open(file_path, 'w') as file:
            json.dump(existing_data, file, indent=4)
        print(f"Updated data saved to {file_path}.")

    except Exception as e:
        print(f"An error occurred while updating {file_path}: {e}")

@functools.lru_cache(maxsize=1)
def load_product_data(file_path='database/product.json'):
    """Load product data from a local JSON file and cache it."""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                products_db = json.load(file)
        else:
            print(f"{file_path} not found.")
            products_db = []
    except Exception as e:
        print(f"An error occurred: {e}")
        products_db = []
    return products_db

@app.post('/api/survey')
async def survey_data(request: Request):
    data = await request.json()
    if not data:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON data")

    product_name = data.get('product_name')
    brand_name = data.get('brand_name')
    questions_answers = data.get('answers')

    if not all([product_name, brand_name, questions_answers]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    result = await process_survey_data(data)
    return JSONResponse(result, status_code=200)

async def process_survey_data(data):
    product_name = data.get('product_name')
    brand_name = data.get('brand_name')
    questions_answers = data.get('answers')
    product_link = ""
    product_db = load_product_data()
    for product in product_db:
        if (product["Product Name"].lower() == product_name.lower() and
            product["Brand Name"].lower() == brand_name.lower()):
            product_link = product["Product Link"]
            break

    response = {
        "product_name": product_name,
        "brand_name": brand_name,
        "questions_answers": questions_answers,
        "product_link": product_link
    }

    model_data = model_pkl_formatter(response)
    from model import mvp_model
    output = await mvp_model(model_data)

    response.update({
        "results": str(output[0]),
    })

    add_data_to_json(response)
    return response

def model_pkl_formatter(response):
    custom_concerns = {
        "Aging (fine lines/wrinkles, loss of firmness/elasticity)": "Aging",
        "Acne/blemishes": "Acne",
        "Hyperpigmentation/Dark Spots": "Dark spots",
        "Uneven texture": "Uneven texture ",
        "Pores":"Pores "
    }
    input_data = {
        'Skin_Type_C': [],
        'Skin_Concern_C': [],
        'Degree_of_Concern_C': [],
        'Fragrance_Preference_C': [],
        'Sensitivity_C': [],
        'Product Link': []
    }
    questions_answers = response['questions_answers']
    skin_type = questions_answers.get('What is your skin type?', [""])[0]
    if skin_type:
        input_data['Skin_Type_C'] = [skin_type]

    concerns = questions_answers.get('What is the primary skin concern you are hoping to address with this product?(Select One)', [""])[0]
    if concerns:
        if concerns in custom_concerns:
            input_data['Skin_Concern_C'] = [custom_concerns[concerns]]
        else:
            input_data['Skin_Concern_C'] = [concerns]

    severity = questions_answers.get('How severe is this', [""])[0]
    if severity:
        input_data['Degree_of_Concern_C'] = [severity]
    fragrance_preference = questions_answers.get('How do you feel about fragrances?', [""])[0]

    if fragrance_preference:
        if fragrance_preference == "Hate them":
            input_data['Fragrance_Preference_C'] = ["No fragrance"]
        elif fragrance_preference == "Love them":
            input_data['Fragrance_Preference_C'] = ["Yes fragrance"]
        elif fragrance_preference == "Don't Care":
            input_data['Fragrance_Preference_C'] = ["Don't care"]
        else:
            input_data['Fragrance_Preference_C'] = ["No fragrance"]

    sensitivity = questions_answers.get('Does your skin react poorly to new products?', [""])[0]
    if sensitivity:
        input_data['Sensitivity_C'] = [sensitivity]

    input_data['Product Link'] = [response.get('product_link', "")]
    
    return input_data


@app.get('/api/product/{product_name}/{brand_name}')
async def check_product(product_name: str, brand_name: str):
    product_db = load_product_data()
    for product in product_db:
        if (product["Product Name"].lower() == product_name.lower() and
            product["Brand Name"].lower() == brand_name.lower()):
            return JSONResponse({"message": "Product found", "product": product}, status_code=200)
    raise HTTPException(status_code=404, detail="Product not found")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
