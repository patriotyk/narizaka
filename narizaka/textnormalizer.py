import regex
# from num2words import num2words
import unicodedata

# simple_replacements = {
#     '№' : 'номер',
#     '§': 'номер'
# }

# masc_replacments_dict = {
#     '%':['відсоток', 'відсотки', 'відсотків'],
#     'мм': ['міліметр', 'міліметри', 'міліметрів'],
#     'см': ['сантиметр', 'сантиметри', 'сантиметрів'],
#     'мм': ['міліметр', 'міліметри', 'міліметрів'],
#     # 'м': ['метр', 'метри', 'метрів'],
#     'км': ['кілометр', 'кілометри', 'кілометрів'],
#     'гц': ['герц', 'герци', 'герців'],
#     'кгц': ['кілогерц', 'кілогерци', 'кілогерців'],
#     'мгц': ['мегагерц', 'мегагерци', 'мегагерців'],
#     'ггц': ['гігагерц', 'гігагерци', 'гігагерців'],
#     'вт': ['ват', 'вати', 'ватів'],
#     'квт': ['кіловат', 'кіловати', 'кіловатів'],
#     'мвт': ['мегават', 'мегавати', 'мегаватів'],
#     'гвт': ['гігават', 'гігавати', 'гігаватів'],
#     'дж': ['джоуль', 'джоулі', 'джоулів'],
#     'кдж': ['кілоджоуль', 'кілоджоулі', 'кілоджоулів'],
#     'мдж': ['мегаджоуль', 'мегаджоулі', 'мегаджоулів'],
#     'см2': ['сантиметр квадратний', 'сантиметри квадратні', 'сантиметрів квадратних'],
#     'м2': ['метр квадратний', 'метри квадратні', 'метрів квадратних'],
#     'м2': ['кілометр квадратний', 'кілометри квадратні', 'кілометрів квадратних'],
#     '$': ['долар', 'долари', 'доларів'],
#     '€': ['євро', 'євро', 'євро'],
# }

# fem_replacments_dict = {
#     'кал': ['калорія', 'калорії', 'калорій'],
#     'ккал': ['кілокалорія', 'кілокалорії', 'кілокалорій'],
#     'грн': ['гривня', 'гривні', 'гривень'],
#     'грв': ['гривня', 'гривні', 'гривень'],
#     '₴': ['гривня', 'гривні', 'гривень'],
# }

# neu_replacments_dict = {
#      '€': ['євро', 'євро', 'євро'],
# }

# all_replacments_keys = list(masc_replacments_dict.keys()) + list(fem_replacments_dict.keys()) + list(neu_replacments_dict.keys())

# #Ordinal types
# #Називний
# ordinal_nominative_masculine_cases = ('й','ий')
# ordinal_nominative_feminine_cases = ('a','ша', 'я')
# ordinal_nominative_neuter_cases = ('е',)

# #Родовий
# ordinal_genitive_masculine_case = ('го','о',)
# ordinal_genitive_feminine_case = ('ї', 'ої')


# #Давальний
# ordinal_dative_masculine_case = ('му',)
# ordinal_dative_feminine_case = ('й','ій')

# #Знахідний
# ordinal_accusative_masculine_case = ordinal_genitive_masculine_case
# ordinal_accusative_feminine_case = ('у',)

# #Орудний
# ordinal_instrumental_masculine_case = ('им', 'ім')
# ordinal_instrumental_feminine_case = ('ю')


# #Місцевий
# # ordinal_locative_masculine_case = ordinal_dative_masculine_case
# # ordinal_locative_feminine_case = ordinal_dative_feminine_case

# numcases_r = regex.compile(rf'((?:^|\s)(\d+)\s*(\-?)(([^\d,]*?)|(\-\.+))(?:\.|,|:|-)?)(\s+[^,.:\-]|$)', regex.IGNORECASE, regex.UNICODE)

# print(numcases_r)
# cardinal_genitive_endings = ('а', 'e', 'є', 'й')
# ordinal_genitive_cases = ('року',)

# def number_form(number):
#     if number[-1] == "1":
#         return 0
#     elif number[-1] in ("2", "3", "4"):
#         return 1
#     else:
#         return 2

# def replace_cases(number, dash, case='', next_word=''):
#     print(f'{number}, {dash}, {case}, {next_word}')
#     gender = 'masculine'
#     m_case = 'nominative'
#     to = 'ordinal'
#     repl = ''
#     if not dash:
#         if case in all_replacments_keys:
#             if case in masc_replacments_dict.keys():
#                 repl = masc_replacments_dict.get(case)[number_form(number)]
#                 gender = 'masculine'
#             elif case in fem_replacments_dict.keys():
#                 repl = fem_replacments_dict.get(case)[number_form(number)]
#                 gender = 'feminine'
#             elif case in neu_replacments_dict.keys():
#                 repl = neu_replacments_dict.get(case)[number_form(number)]
#                 gender = 'neuter'
#             to = 'cardinal'
#         else:
#             if len(case) < 3 and case and case[-1] in cardinal_genitive_endings:
#                 m_case = 'genitive'
#                 gender='masculine'
#                 to = 'cardinal'
#             elif case in ordinal_genitive_cases:
#                 to = 'ordinal'
#                 m_case = 'genitive'
#                 repl = case
#             else:
#                 to = 'cardinal'
#                 repl = case
                
#     else:    
#         if case in ordinal_nominative_masculine_cases:
#             m_case = 'nominative'
#             gender = 'masculine'
#         elif case in ordinal_nominative_feminine_cases:
#             m_case = 'nominative'
#             gender = 'feminine'
#         elif case in ordinal_nominative_neuter_cases:
#             m_case = 'nominative'
#             gender = 'neuter'
#         elif case in ordinal_genitive_masculine_case:
#             m_case = 'genitive'
#             gender = 'masculine'
#         elif case in ordinal_genitive_feminine_case:
#             m_case = 'genitive'
#             gender = 'feminine'
#         elif case in ordinal_dative_masculine_case:
#             m_case = 'dative'
#             gender = 'masculine'
#         elif case in ordinal_dative_feminine_case:
#             m_case = 'dative'
#             gender = 'feminine'
#         elif case in ordinal_accusative_feminine_case:
#             m_case = 'accusative'
#             gender = 'feminine'
#         elif case in ordinal_instrumental_masculine_case:
#             m_case = 'instrumental'
#             gender = 'masculine'
#         elif case in ordinal_instrumental_feminine_case:
#             m_case = 'instrumental'
#             gender = 'feminine'
#         else:
#             if case and case[-1] in cardinal_genitive_endings:
#                 m_case = 'genitive'
#                 gender='masculine'
#                 to = 'cardinal'
#                 repl = case
#             else:
#                 print(f'UNKNOWN CASE {number}-{case}')

#     return_str = num2words(number, to=to, lang='uk', case=m_case, gender=gender)
#     if repl:
#         return_str +=  ' ' + repl
#     if not next_word or (next_word and  next_word.strip().isupper()):
#         return_str += '.'
#     return return_str

# def norm(text):
#     text = regex.sub(r'[\t\n]', ' ', text)
#     text = regex.sub(rf"[{''.join(simple_replacements.keys())}]", lambda x: f' {simple_replacements[x.group()]} ', text)
#     text = regex.sub(r"(\d)\s+(\d)", r"\1\2", text)
#     text = regex.sub(r'\s+', ' ', text)
#     text = unicodedata.normalize('NFC', text)
#     matches = numcases_r.finditer(text)
#     pos = 0
#     new_text = ''
#     for m in matches:
#         repl = replace_cases(m.group(2), m.group(3), m.group(4), m.group(7))
#         new_text += text[pos:m.start(0)]+ ' ' + repl
#         pos = m.end(1)
#     new_text += text[pos:]
#     return new_text.strip()

    

import os
from transformers import MBartForConditionalGeneration, AutoTokenizer
import torch

model_name = "skypro1111/mbart-large-50-verbalization-53k-ckpt"
# Directory containing model checkpoints

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# Load tokenizer globally (assuming all models use the same tokenizer)
tokenizer = AutoTokenizer.from_pretrained('facebook/mbart-large-50', device_map=DEVICE,)
tokenizer.src_lang = "uk_XX"  # Приклад встановлення мови вхідних даних
tokenizer.tgt_lang = "uk_XX"  # Встановіть відповідний код мови для української

model = None  # Initialize model variable globally


def load_model():
    """Load the model from a checkpoint."""
    model = MBartForConditionalGeneration.from_pretrained(
        model_name,
        low_cpu_mem_usage=False
    )
    model.eval()  # Перемкнути модель в режим інференсу
    return  model

def norm(input_text):
    """Perform inference using the selected model checkpoint."""
    global model
    if not model:
        model = load_model()
    input_text = f"<verbalization>:{input_text}"
    encoded_input = tokenizer(input_text, return_tensors="pt", padding=True, truncation=True, max_length=1024).to(DEVICE)
    input_text = tokenizer.prepare_seq2seq_batch(src_texts=[input_text],
                                                 src_lang='uk_XX',
                                                 return_tensors="pt",
                                                 padding=True).to(DEVICE)
    # input_ids = input_text["input_ids"]
    output_ids = model.generate(**encoded_input, temperature=0.5, max_length=1024, num_beams=5, early_stopping=True)
    output_text = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    text = regex.sub(r'[\t\n]', ' ', output_text)
    text = regex.sub(r'\s+', ' ', text)
    text = unicodedata.normalize('NFC', text)
    return text