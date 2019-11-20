import requests
import re
import pandas as pd
import datetime as dt
import pytz


def GetVacancies(area, per_page):
    url = 'https://api.hh.ru/vacancies'
    data = {'text': 'Программист', 'area': area, 'per_page': per_page}
    return requests.get(url, params=data).json()


def ClearText(text):
    regex = re.compile('\r\n|<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});')
    return re.sub(regex, '', text)


def ParseVacancies(request):
    return [ParseVacancy(line) for line in request['items']]


def ParseVacancy(line):
    vacancy = dict()
    vacancy['name'] = line['name']
    vacancy['city'] = line['area']['name'] if line['area'] is not None else None
    vacancy['min_salary'] = line['salary']['from'] if line['salary'] is not None else None
    vacancy['max_salary'] = line['salary']['to'] if line['salary'] is not None else None
    vacancy['company'] = line['employer']['name'] if line['employer'] is not None else None
    vacancy['published_at'] = line['published_at']

    info = requests.get('https://api.hh.ru/vacancies/%s' % line['id']).json()

    exp = info['experience']['name'].split(' ') if info['experience'] is not None else None
    if exp[0] == 'От':
        vacancy['min_experience'] = exp[1]
        vacancy['max_experience'] = exp[4] if exp[3] == 'до' else exp[3]
    if exp[0] == 'Более':
        vacancy['min_experience'] = exp[1]
        vacancy['max_experience'] = 0
    if exp[0] == 'Нет':
        vacancy['min_experience'] = 0
        vacancy['max_experience'] = 0

    vacancy['schedule'] = info['schedule']['name'] if info['schedule'] is not None else None
    vacancy['employment'] = info['employment']['name'] if info['employment'] is not None else None

    descr = ClearText(info['description']) if info['description'] is not None else None
    descr_mas_cond1 = descr.split('Условия:')
    descr_mas_cond2 = descr.split('Вам потребуется:')
    descr_mas_cond3 = descr.split('Мы предлагаем:')
    vacancy['description'] = descr

    if len(descr_mas_cond1) > 1:
        vacancy['conditions'] = descr_mas_cond1[1]
    if len(descr_mas_cond2) > 1:
        vacancy['conditions'] = descr_mas_cond2[1]
    if len(descr_mas_cond3) > 1:
        vacancy['conditions'] = descr_mas_cond3[1]

    vacancy['requirement'] = line['snippet']['requirement'] if line['snippet'] is not None else None
    vacancy['responsibility'] = line['snippet']['responsibility'] if line['snippet'] is not None else None

    vacancy['key_skills'] = ''
    for skill in info['key_skills']:
        vacancy['key_skills'] += skill['name'] + '; '
    vacancy['key_skills'] = vacancy['key_skills'][:-2]
    return vacancy


def GetSalaries(data_frame, group_by, num):
    step = (data_frame[group_by].max() - data_frame[group_by].min()) / num
    groups = []
    salary = data_frame[group_by].min()
    count = 0
    while data_frame[group_by].min() <= salary <= data_frame[group_by].max() - step:
        count += 1
        tmp = data_frame[(data_frame[group_by] > salary) & (data_frame[group_by] <= salary + step)]
        tmp.to_csv("GroupsSalary" + "/salary_gr" + str(count) + ".csv", sep=';', encoding='UTF-8-sig')
        groups.append(tmp)
        salary += step
    return groups


def GetNames(data_frame, group_by):
    categories = pd.unique(data_frame[group_by])
    groups = []
    count = 0;
    for category in categories:
        count += 1
        fr = data_frame[data_frame[group_by] == category]
        groups.append(fr)
        fr.to_csv("GroupsName" + "/salary_gr" + str(count) + ".csv", sep=';', encoding='UTF-8-sig')
    return groups


def WriteInfo(data_frame, unique, count, directory_name, file_name):
    unique_dict = []
    vacancy = dict()
    q = dict()
    names = data_frame[unique]
    for n in names:
        if n not in q:
            if n == '':
                n = 'nan'
            if n != 'nan':
                q[n] = 1
        else:
            if n == '':
                n = 'nan'
            if n != 'nan':
                q[n] += 1
    vacancy[unique+'s'] = str(q)
    date = pd.to_datetime(df['published_at'], utc=True).dt.tz_convert('US/Eastern')
    days = (dt.datetime.now(pytz.timezone('US/Eastern')) - date).astype('timedelta64[D]')
    vacancy['minCountDays'] = days.min()
    vacancy['maxCountDays'] = days.max()
    vacancy['avgCountDays'] = days.mean()
    vacancy['experience'] = data_frame['min_experience'].value_counts().to_string().replace('\n', ';')
    vacancy['employment'] = data_frame['employment'].value_counts().to_string().replace('\n', ';')
    vacancy['schedule'] = data_frame['schedule'].value_counts().to_string().replace('\n', ';')
    skills = data_frame['key_skills'].str.split(';')
    vacancy_skills = {}
    for d in skills:
        for sk in d:
            if sk not in vacancy_skills:
                if sk != '':
                    vacancy_skills[sk] = 1
            else:
                if sk != '':
                    vacancy_skills[sk] += 1
    vacancy['skills'] = str(vacancy_skills)
    unique_dict.append(vacancy)
    pd.DataFrame(unique_dict).to_csv(directory_name + "/" + file_name + str(count) + ".csv", sep=';', encoding='UTF-8-sig')


df = pd.DataFrame(ParseVacancies(GetVacancies(95, 100)))
for i in range(1, 5):
    df = df.append((ParseVacancies(GetVacancies(i, 100))))


df = df.sort_values(['max_salary', 'min_salary'], ascending=[False, True])
df.to_csv("Vacancies.csv", sep=';', encoding='UTF-8-sig')


groups = GetSalaries(df, 'max_salary', 10)
for i in range(0, 10):
    WriteInfo(groups[i], 'name', i + 1, "GroupsSalary", "info_salary_gr")


groups = GetNames(df, 'name')
i = 0
for gr in groups:
    WriteInfo(gr, 'min_salary', i + 1, "GroupsName", "info_min_gr")
    i += 1


i = 0
for gr in groups:
    WriteInfo(gr, 'max_salary', i + 1, "GroupsName", "info_max_gr")
    i += 1
