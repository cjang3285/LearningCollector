# 백준 1260번: DFS와 BFS
# 난이도: Silver II
# 문제: 그래프를 DFS로 탐색한 결과와 BFS로 탐색한 결과를 출력하는 프로그램

from collections import deque

def dfs(graph, v, visited):
    visited[v] = True
    print(v, end=' ')

    for i in sorted(graph[v]):
        if not visited[i]:
            dfs(graph, i, visited)

def bfs(graph, start):
    visited = [False] * (len(graph))
    queue = deque([start])
    visited[start] = True

    while queue:
        v = queue.popleft()
        print(v, end=' ')

        for i in sorted(graph[v]):
            if not visited[i]:
                queue.append(i)
                visited[i] = True

n, m, v = map(int, input().split())
graph = [[] for _ in range(n + 1)]

for _ in range(m):
    a, b = map(int, input().split())
    graph[a].append(b)
    graph[b].append(a)

visited = [False] * (n + 1)
dfs(graph, v, visited)
print()
bfs(graph, v)
