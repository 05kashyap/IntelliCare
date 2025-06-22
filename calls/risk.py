import numpy as np
import pandas as pd
import os

import requests
url = "https://api.sarvam.ai/translate"
payload = {
    "input": "ನಾನು ಆತ್ಮಹತ್ಯೆ ಮಾಡಿಕೊಳ್ಳುತ್ತೇನೆ",
    "source_language_code": "auto",
    "target_language_code": "en-IN"
}
headers = {
    "api-subscription-key": "78ea6d74-9f90-4f0a-9f87-1cc7e1c27d6e",
    "Content-Type": "application/json"
}
response = requests.post(url, json=payload, headers=headers)
print(response.json())
text = response.json()['translated_text']

from setfit import SetFitModel

model = SetFitModel.from_pretrained("richie-ghost/setfit-mental-bert-base-uncased-Suicidal-Topic-Check")

descr_mapper = {
    "Presence of a loved one": "This class reflects emotional pain rooted in loneliness, lack of connection, or craving emotional support. The person expresses a desire for someone to talk to, lean on, or simply be there during hard times.",
    "Previous attempt": "Refers to prior suicide attempts and the individual's reflections or ambivalence about surviving. There's a mix of regret, fear, and unresolved pain. These expressions show how the trauma of previous attempts lingers.",
    "Ability to take care of oneself": "Shows functional decline, losing interest in hobbies, neglecting responsibilities, and struggling to maintain basic routines. It's a key behavioral indicator of depression, often linked to withdrawal and burnout.",
    "Ability to hope for change": "Reflects a deep sense of hopelessness and despair, often with a desperate wish for something to improve. People in this category express feeling stuck, drained, or unable to see a way forward.",
    "Other": "Mentions non-depressive or positive aspects of life, such as hobbies, nature, learning, or routines. These are grounding statements, and may come from someone coping or recovering, or simply from unrelated content.",
    "Suicidal planning": "Involves explicit thoughts, intentions, or plans about suicide. This is the most acute and dangerous form of ideation, requiring immediate attention in real-life settings.",
    "Ability to control oneself": "Captures the struggle with impulse control and emotional regulation. Individuals here feel out of control, often battling rapid thoughts, urges, or emotional breakdowns that they can't manage.",
    "Consumption": "Describes maladaptive coping behaviors, especially substance use (like alcohol) used to escape pain. It reflects how the person is using external substances to numb or survive emotional turmoil."
}

risk_measure = {
    "Presence of a loved one": "low risk",
    "Previous attempt": "high risk",
    "Ability to take care of oneself": "medium risk",
    "Ability to hope for change": "low risk",
    "Other": "no risk",
    "Suicidal planning": "ALERT!",
    "Ability to control oneself": "low risk",
    "Consumption": "medium risk"
}

preds = model(text)

print(f'{preds}: {descr_mapper[preds]}')
print(f'Risk Measure: {risk_measure[preds]}')