import regex
from num2words import num2words
import unicodedata


masc_replacments_dict = {
    '%':['відсоток', 'відсотки', 'відсотків'],
    'мм': ['міліметр', 'міліметри', 'міліметрів'],
    'см': ['сантиметр', 'сантиметри', 'сантиметрів'],
    'мм': ['міліметр', 'міліметри', 'міліметрів'],
    # 'м': ['метр', 'метри', 'метрів'],
    'км': ['кілометр', 'кілометри', 'кілометрів'],
    'гц': ['герц', 'герци', 'герців'],
    'кгц': ['кілогерц', 'кілогерци', 'кілогерців'],
    'мгц': ['мегагерц', 'мегагерци', 'мегагерців'],
    'ггц': ['гігагерц', 'гігагерци', 'гігагерців'],
    'вт': ['ват', 'вати', 'ватів'],
    'квт': ['кіловат', 'кіловати', 'кіловатів'],
    'мвт': ['мегават', 'мегавати', 'мегаватів'],
    'гвт': ['гігават', 'гігавати', 'гігаватів'],
    'дж': ['джоуль', 'джоулі', 'джоулів'],
    'кдж': ['кілоджоуль', 'кілоджоулі', 'кілоджоулів'],
    'мдж': ['мегаджоуль', 'мегаджоулі', 'мегаджоулів'],
    'см2': ['сантиметр квадратний', 'сантиметри квадратні', 'сантиметрів квадратних'],
    'м2': ['метр квадратний', 'метри квадратні', 'метрів квадратних'],
    'м2': ['кілометр квадратний', 'кілометри квадратні', 'кілометрів квадратних'],
    '$': ['долар', 'долари', 'доларів'],
    '€': ['євро', 'євро', 'євро'],
}

fem_replacments_dict = {
    'кал': ['калорія', 'калорії', 'калорій'],
    'ккал': ['кілокалорія', 'кілокалорії', 'кілокалорій'],
    'грн': ['гривня', 'гривні', 'гривень'],
    'грв': ['гривня', 'гривні', 'гривень'],
    '₴': ['гривня', 'гривні', 'гривень'],
}

neu_replacments_dict = {
     '€': ['євро', 'євро', 'євро'],
}

all_replacments_keys = list(masc_replacments_dict.keys()) + list(fem_replacments_dict.keys()) + list(neu_replacments_dict.keys())
replacments_keys_r = '|'.join([f'({i})' for i in all_replacments_keys])



#Ordinal types
#Називний
ordinal_nominative_masculine_cases = ('й','ий')
ordinal_nominative_feminine_cases = ('a','ша', 'я')
ordinal_nominative_neuter_cases = ('е',)

ordinal_nominative_masculine_cases_r = '|'.join([f'({i})' for i in ordinal_nominative_masculine_cases])
ordinal_nominative_feminine_cases_r = '|'.join([f'({i})' for i in ordinal_nominative_feminine_cases])
ordinal_nominative_neuter_cases_r = '|'.join([f'({i})' for i in ordinal_nominative_neuter_cases])

#Родовий
ordinal_genitive_masculine_case = ('го','о', 'року', 'р')
ordinal_genitive_feminine_case = ('ї', 'ої')

ordinal_genitive_masculine_case_r = '|'.join([f'({i})' for i in ordinal_genitive_masculine_case])
ordinal_genitive_feminine_case_r = '|'.join([f'({i})' for i in ordinal_genitive_feminine_case])


#Давальний
ordinal_dative_masculine_case = ('му',)
ordinal_dative_feminine_case = ('й','ій')

ordinal_dative_masculine_case_r = '|'.join([f'({i})' for i in ordinal_dative_masculine_case])
ordinal_dative_feminine_case_r = '|'.join([f'({i})' for i in ordinal_dative_feminine_case])

#Знахідний
ordinal_accusative_masculine_case = ordinal_genitive_masculine_case
ordinal_accusative_feminine_case = ('у',)
ordinal_accusative_feminine_case_r = '|'.join([f'({i})' for i in ordinal_accusative_feminine_case])

#Орудний
ordinal_instrumental_masculine_case = ('им', 'ім')
ordinal_instrumental_feminine_case = ('ю')

ordinal_instrumental_masculine_case_r = '|'.join([f'({i})' for i in ordinal_instrumental_masculine_case])
ordinal_instrumental_feminine_case_r = '|'.join([f'({i})' for i in ordinal_instrumental_feminine_case])

#Місцевий
# ordinal_locative_masculine_case = ordinal_dative_masculine_case
# ordinal_locative_feminine_case = ordinal_dative_feminine_case

numcases_r = regex.compile(rf'(\d+)\s*(\-)?\s*({replacments_keys_r}|'+\
                           rf'{ordinal_nominative_masculine_cases_r}|{ordinal_nominative_feminine_cases_r}|{ordinal_nominative_neuter_cases_r}|'+\
                           rf'{ordinal_genitive_masculine_case_r}|{ordinal_genitive_feminine_case_r}|'+\
                           rf'{ordinal_dative_masculine_case_r}|{ordinal_dative_feminine_case_r}|{ordinal_accusative_feminine_case_r}|'+\
                           rf'{ordinal_instrumental_masculine_case_r}|{ordinal_instrumental_feminine_case_r}|(-.*?))\.?(\s|$)', regex.IGNORECASE, regex.UNICODE)

print(numcases_r)
cardinal_genitive_endings = ('a', 'e', 'є', 'й')

def number_form(number):
    if number[-1] == "1":
        return 0
    elif number[-1] in ("2", "3", "4"):
        return 1
    else:
        return 2

def replace_cases(number, dash, case):
    gender = 'masculine'
    m_case = 'nominative'
    to = 'ordinal'
    repl = ''
    if not dash:
        if case in all_replacments_keys:
            if case in masc_replacments_dict.keys():
                repl = masc_replacments_dict.get(case)[number_form(number)]
                gender = 'masculine'
            elif case in fem_replacments_dict.keys():
                repl = fem_replacments_dict.get(case)[number_form(number)]
                gender = 'feminine'
            elif case in neu_replacments_dict.keys():
                repl = neu_replacments_dict.get(case)[number_form(number)]
                gender = 'neuter'
            to = 'cardinal'
        else:
            laschar = case[-1]
            if len(case) < 3 and laschar in cardinal_genitive_endings:
                m_case = 'genitive'
                gender='masculine'
                to = 'cardinal'
            else:
                m_case = 'genitive'
                if case[0] == '-':
                    to = 'cardinal'
                    repl = case[1:]
                else:
                    to = 'ordinal'
                    repl = case
                #print(f'UNKNOWN CASEdd {number} {case}')
    else:    
        if case in ordinal_nominative_masculine_cases:
            m_case = 'nominative'
            gender = 'masculine'
        elif case in ordinal_nominative_feminine_cases:
            m_case = 'nominative'
            gender = 'feminine'
        elif case in ordinal_nominative_neuter_cases:
            m_case = 'nominative'
            gender = 'neuter'
        elif case in ordinal_genitive_masculine_case:
            m_case = 'genitive'
            gender = 'masculine'
        elif case in ordinal_genitive_feminine_case:
            m_case = 'genitive'
            gender = 'feminine'
        elif case in ordinal_dative_masculine_case:
            m_case = 'dative'
            gender = 'masculine'
        elif case in ordinal_dative_feminine_case:
            m_case = 'dative'
            gender = 'feminine'
        elif case in ordinal_accusative_feminine_case:
            m_case = 'accusative'
            gender = 'feminine'
        elif case in ordinal_instrumental_masculine_case:
            m_case = 'instrumental'
            gender = 'masculine'
        elif case in ordinal_instrumental_feminine_case:
            m_case = 'instrumental'
            gender = 'feminine'
        else:
            print(f'UNKNOWN CASE {number}-{case}')

    return_str = num2words(number, to=to, lang='uk', case=m_case, gender=gender)
    if repl:
        return_str +=  ' ' + repl
    return return_str

def norm(text):
    text = regex.sub(r'[\t\n]', ' ', text)
    text = regex.sub(r'\s+', ' ', text)
    text = unicodedata.normalize('NFC', text)
    text = text.lower()
    matches = numcases_r.finditer(text)
    pos = 0
    new_text = ''
    for m in matches:
        repl = replace_cases(m.group(1), m.group(2), m.group(3))
        new_text += text[pos:m.start(0)] + repl + ' '
        pos = m.end(0)
    new_text += text[pos:]
    return new_text

    

#1-го квітня, на 1-му поверсі Яринка загубила 2грн але знайшла 5€. Але її 4-річна сестричка забрала 50% її знахідки.
#Також 2003 року щось там сталося і 40-річний чоловік помер. Його знайшли через 3 години.