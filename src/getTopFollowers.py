"""
   Copyright 2020-2025 Yufan You <https://github.com/ouuan>

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

   Adaptado de https://github.com/ouuan/ouuan/blob/master/src/getTopFollowers.py
   para o profile frederico-kluser/frederico-kluser:
   - avatares com tamanho fixo (s=100) e tabela com quebras de linha;
   - TODOS os seguidores listados, ordenados por número de seguidores (até 21) —
     os filtros anti-spam de atividade/quota do original foram removidos de
     propósito: existem para perfis com milhares de seguidores e escondiam
     seguidores reais de contas pequenas;
   - nomes reais via GraphQL (fallback para o login);
   - mensagem amigável quando não há seguidores;
   - falha alta quando os marcadores do README não existem.
"""

import requests
import json
import sys
import re
from time import sleep
from functools import partial

NL = chr(10)


def build_followers_html(followers):
    followers = sorted(set(followers), reverse=True)

    if not followers:
        return "> ✨ Nenhum seguidor por enquanto — seja o primeiro!"

    rows = []
    limit = min(len(followers), 21)
    for i in range(limit):
        login = followers[i][1]
        id = followers[i][2]
        name = followers[i][3] or followers[i][1]
        if i % 7 == 0:
            rows.append('  <tr>')
        rows.append(NL.join([
            '    <td align="center">',
            '      <a href="https://github.com/' + login + '">',
            '        <img src="https://avatars.githubusercontent.com/u/' + str(id) + '?s=100&v=4" width="100px;" alt="' + login + '"/>',
            '      </a>',
            '      <br />',
            '      <a href="https://github.com/' + login + '">' + name + '</a>',
            '    </td>',
        ]))
        if i % 7 == 6 or i == limit - 1:
            rows.append('  </tr>')
    return '<table>' + NL + NL.join(rows) + NL + '</table>'


if __name__ == "__main__":
    assert(len(sys.argv) == 4)
    handle = sys.argv[1]
    token = sys.argv[2]
    readmePath = sys.argv[3]

    print = partial(print, flush = True)

    headers = {
        "Authorization": "token " + token
    }

    followers = []
    cursor = None
    retryCount = 0
    cwnd = 1
    ssthresh = 20

    while True:
        after_part = ', after: "' + cursor + '"' if cursor else ''
        query = (
            'query {'
            ' user(login: "' + handle + '") {'
            ' followers(first: ' + str(cwnd) + after_part + ') {'
            ' pageInfo {'
            ' endCursor'
            ' hasNextPage'
            ' }'
            ' nodes {'
            ' login'
            ' name'
            ' databaseId'
            ' followers {'
            ' totalCount'
            ' }'
            ' }'
            ' }'
            ' }'
            '}'
        )
        try:
            response = requests.post("https://api.github.com/graphql", json.dumps({ "query": query }), headers = headers)
        except Exception as e:
            if retryCount >= 3:
                raise e
            print("Network error, retrying")
            sleep(5)
            retryCount += 1
            continue
        if not response.ok or "data" not in response.json():
            if retryCount < 3:
                retryCount += 1
                if "Retry-After" in response.headers:
                    wait = int(response.headers["Retry-After"])
                    print("Rate limit exceeded, retry after " + str(wait) + " seconds")
                    sleep(wait)
                    continue
                ssthresh = cwnd // 2
                cwnd = 1
                print("Error, entering slow start with ssthresh = " + str(ssthresh))
                sleep(5)
                continue
            print(query)
            print(response.status_code)
            print(response.headers)
            print(response.text)
            exit(1)
        retryCount = 0
        if cwnd < ssthresh:
            cwnd = min(ssthresh, cwnd * 2)
        else:
            cwnd += 1
        res = response.json()["data"]["user"]["followers"]
        try:
            for follower in res["nodes"]:
                followerNumber = follower["followers"]["totalCount"]
                login = follower["login"]
                name = follower["name"]
                id = follower["databaseId"]
                followers.append((followerNumber, login, id, name if name else login))
                print(followers[-1])
        except TypeError as e:
            retryCount += 1
            if retryCount >= 3:
                print(res)
                raise e
            print("Error: " + str(e))
            ssthresh = cwnd // 2
            cwnd = 1
            sleep(5)
            continue
        sys.stdout.flush()
        if not res["pageInfo"]["hasNextPage"]:
            break
        cursor = res["pageInfo"]["endCursor"]

    html = build_followers_html(followers)

    with open(readmePath, "r") as readme:
        content = readme.read()

    if "<!--START_SECTION:top-followers-->" not in content or "<!--END_SECTION:top-followers-->" not in content:
        print("Marcadores <!--START_SECTION:top-followers--> não encontrados no README.md")
        exit(1)

    newContent = re.sub(
        r'(?s)<!--START_SECTION:top-followers-->.*?<!--END_SECTION:top-followers-->',
        "<!--START_SECTION:top-followers-->" + NL + html + NL + "<!--END_SECTION:top-followers-->",
        content,
    )

    if newContent == content:
        print("Nada a atualizar — a seção de seguidores já está em dia")
    else:
        with open(readmePath, "w") as readme:
            readme.write(newContent)
        print("Top followers atualizados no README.md (" + str(min(len(followers), 21)) + " seguidores)")