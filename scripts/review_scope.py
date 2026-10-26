"""Conservative review scope; dependencies indicate what to inspect, never auto-apply changes."""
def affected(spec, requirement_ids):
    changed = set(requirement_ids)
    rules = {r['id'] for req in spec.get('requirements', []) if req['id'] in changed for r in req.get('rule_details', [])}
    interactions = [i for i in spec.get('interactions', []) if changed.intersection(i.get('requirement_ids', [])) or rules.intersection(i.get('rule_ids', []))]
    pages = [p for p in spec.get('pages', []) if changed.intersection(p.get('requirement_ids', [])) or any(i.get('page_id', i.get('page')) == p['id'] for i in interactions)]
    return {'rules': sorted(rules), 'pages': [p['id'] for p in pages],
            'states': [{'page':p['id'], 'state':s['id']} for p in pages for s in p.get('states', [])],
            'interactions': [i['id'] for i in interactions],
            'acceptance': sorted({a['id'] for req in spec.get('requirements', []) if req['id'] in changed for a in req.get('acceptance', [])}),
            'diagrams': [d['id'] for d in spec.get('diagrams', []) if d.get('requirement_id') in changed or any(changed.intersection(n.get('requirement_ids', [])) for n in d.get('nodes', [])) or any(rules.intersection(e.get('rule_ids', [])) for e in d.get('edges', []))],
            'note': '保守列出受影响功能的所有状态；删除项及未结构化依赖还需对照差异/原始方案复核，不代表均需重写。'}
