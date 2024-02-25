import os

import pandas as pd

laptop_df = pd.read_csv("laptop_database.csv")

import json
import requests
from web_app import keep_alive

import discord

API_URL = "https://api-inference.huggingface.co/models/"

MODEL_NAMES = {
  "text-classification": "TirkNork/laptop_sentence_classfication_wangChanBERTa",
  "token-classification": "Ponlawat1645/SaleAI-token-classification",
  "zero-shot-classification": "facebook/bart-large-mnli",
}

ENTITIES = [
  "brand", "model", "processor_brand", "processor_name", "ram", "memory",
  "price"
]

IDS_TO_TOKENS = {
  'LABEL_0': 'O',
  'LABEL_1': 'B-brand',
  'LABEL_2': 'I-brand',
  'LABEL_3': 'B-model',
  'LABEL_4': 'I-model',
  'LABEL_5': 'B-processor_brand',
  'LABEL_6': 'I-processor_brand',
  'LABEL_7': 'B-processor_name',
  'LABEL_8': 'I-processor_name',
  'LABEL_9': 'B-ram',
  'LABEL_10': 'I-ram',
  'LABEL_11': 'B-memory',
  'LABEL_12': 'I-memory',
  'LABEL_13': 'B-price',
  'LABEL_14': 'I-price'
}

class MyClient(discord.Client):
  def __init__(self, model_name):
    super().__init__(intents=discord.Intents.default())
    huggingface_token = os.environ['HUGGINGFACE_TOKEN']
    self.headers = {"Authorization": f"Bearer {huggingface_token}"}

  def query(self, endpoint, payload):
    data = json.dumps(payload)
    response = requests.request("POST",
                                endpoint,
                                headers=self.headers,
                                data=data)
    return json.loads(response.content.decode("utf-8"))

  async def on_ready(self):
    print('Logged in as')
    print(self.user.name)
    print(self.user.id)
    print('------')

  async def on_message(self, message):
    if message.author.id == self.user.id:
      return

    payload = message.content

    async with message.channel.typing():
      prediction = self.text_classification(payload)
      
      if prediction[0][0]["label"] == "Request":
        entity_slot = self.token_classification(payload)
  
        for entity in entity_slot:
          if entity_slot[entity] != "":
            entity_slot[entity] = self.entity_similarity(entity_slot[entity], entity)

        print(entity_slot)
  
        bot_response = self.database_querying(entity_slot, "star")
      else:
        bot_response = "คุณลูกค้าสามารถบอกข้อมูลของโน๊ตบุ๊คที่สนใจได้เลย เช่น อยากได้โน๊ตบุ๊คยี่ห้อ XXX ราคาไม่เกิน XXX บาท"

    await message.channel.send(bot_response)

  def text_classification(self, payload):
    prediction = self.query(API_URL + MODEL_NAMES["text-classification"], payload)

    return prediction

  def token_classification(self, payload):
    tokens = self.query(API_URL + MODEL_NAMES["token-classification"], payload)
    entity_slot = self.slot_filling(tokens)

    return entity_slot

  def zero_shot_classification(self, token, labels):
    current_labels = labels.copy()

    while True:
      data = {"inputs": token, "parameters": {"candidate_labels": current_labels[0:10]}}
      prediction = self.query(API_URL + MODEL_NAMES["zero-shot-classification"], data)["labels"][0]
      current_labels.append(prediction)

      if len(current_labels) > 10:
        current_labels = current_labels[10:].copy()
      else: break

    return prediction
    
  def find_unique(self, entity):
    labels = [label for label in laptop_df[entity].unique()]
    
    return labels

  def entity_similarity(self, entity, label):
    if label == "price" or label == "memory":
      similar_entity = int("".join([char for char in entity if char.isdigit()]))
    else:
      candidate_labels = self.find_unique(label)
      similar_entity = self.zero_shot_classification(entity, candidate_labels)

    return similar_entity

  def slot_filling(self, tokens):
    entity_slot = {entity: str() for entity in ENTITIES}

    for token in tokens:
      entity = IDS_TO_TOKENS[token["entity_group"]]

      if entity != "O":
        entity_slot[entity.split("-")[1]] += token["word"]

    return entity_slot

  def database_querying(self, params, sort_by=None):
      query = pd.Series(True, index=laptop_df.index)
  
      for key, value in params.items():
        if value != '':
          if key == 'price' or key == 'memory':
              query &= (pd.to_numeric(laptop_df[key]) < value)
          else:
              query &= (laptop_df[key] == value)

      results = laptop_df[query].sort_values(by=sort_by, ascending=False)[:3]
  
      return results

def main():
  client = MyClient('Ponlawat1645/SaleAI-token-classification')
  keep_alive()
  client.run(os.environ['DISCORD_TOKEN'])

if __name__ == '__main__':
  main()
