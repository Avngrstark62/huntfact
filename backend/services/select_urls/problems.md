# ⚠️ Problems (important)

## ❌ 1. Using `query` as identifier (fragile)

```python
selected_item = next(
    (s for s in result.items if s.query == query),
)
```

### Problem:

* Queries are **not guaranteed unique**
* Even worse: LLM may slightly **modify the string**
* Boom → mismatch → empty results

### Fix (must do):

Use **stable IDs**

```python
# before sending to LLM
for i, item in enumerate(items_with_urls):
    item["_id"] = i
```

Prompt:

```
ID: 3
QUERY: ...
```

Schema:

```python
class SelectedUrlItem(BaseModel):
    id: int
    selected_indices: List[int]
```

---

## ❌ 2. No guard against invalid indices

```python
if idx < len(urls)
```

### Problem:

* LLM can return:

  * duplicates → `[1,1,2]`
  * <3 indices → `[1,2]`
  * garbage → `[100, -1]`

### Fix:

```python
indices = list(set(selected_item.selected_indices))
indices = [i for i in indices if 0 <= i < len(urls)]

if len(indices) < 3:
    indices += list(range(len(urls)))[:3-len(indices)]
```

---

## ❌ 3. Prompt is still too long (hidden token leak)

You repeated:

* credibility hierarchy
* strategy
* instructions

👉 This costs ~300–400 tokens **every call**

### Fix:

Move to **system prompt only once**

User prompt should be:

```
Select 3 indices per query.
Return JSON.
```

👉 saves ~30–40% tokens

---

## ❌ 4. No pre-filtering (missed easy win)

Right now:

* 10 URLs per query → LLM sees all

👉 You can cut to **5 URLs before LLM**

### Add:

```python
def prefilter(urls):
    # remove low-quality domains
    blacklist = ["reddit.com", "pinterest.com"]
    return [
        u for u in urls
        if not any(b in u["href"] for b in blacklist)
    ][:5]
```

👉 reduces tokens **2× immediately**

---

## ❌ 5. No domain diversity pre-check

You’re letting LLM solve everything.

👉 Cheaper to enforce partially in code:

```python
seen = set()
unique_urls = []
for u in urls:
    d = extract_domain(u["href"])
    if d not in seen:
        seen.add(d)
        unique_urls.append(u)
```

---

## ⚠️ 6. Output format ambiguity

You wrote:

```
Return the indices as a JSON list.
```

But schema expects:

```json
{
  "items": [
    { "query": "...", "selected_indices": [...] }
  ]
}
```

👉 mismatch risk

---
