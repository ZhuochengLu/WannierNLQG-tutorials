#!/usr/bin/env python3
"""Check the active shallow tree; historical scientific tests remain with their archive."""
from pathlib import Path
import ast,hashlib,json,os,re,tomllib
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
ROOT=Path(__file__).resolve().parents[1]
def check_material_requirements(rows,materials,example_paths):
    consumer=(ROOT/'scripts/tutorial_input.jl').read_text()
    path_fields=re.findall(r'"([a-z_]+)"',re.search(r'const MODEL_PATH_FIELDS = \((.*?)\)',consumer,re.S).group(1))
    assert path_fields==materials['model_path_fields']
    suffixes=re.findall(r'"(\.[a-z]+)"',re.search(r'seed \* ext for ext in \((.*?)\)',consumer,re.S).group(1))
    assert suffixes==materials['seed_required_suffixes']
    required=set();bindings=set()
    for row in rows:
        path=ROOT/row['input'];model=tomllib.loads(path.read_text()).get('model',{})
        for field in path_fields:
            value=model.get(field)
            if not value:continue
            logical=Path(os.path.abspath(path.parent/value)).relative_to(ROOT).as_posix()
            bindings.add(logical);required.add(logical)
            if field=='seedname':required.update(logical+ext for ext in materials['seed_required_suffixes'])
    assert required=={x['logical_path']for x in materials['requirements']}
    assert bindings==set(materials['binding_keys'])==set(example_paths)

def check_inline_provenance(figure):
    """Validate an intact embedded source record without upgrading scientific status."""
    source = figure.get('provenance_source')
    if source is None:
        assert 'provenance' not in figure, 'Provenance payload lacks its migration identity'
        return 0
    assert isinstance(source, dict), 'Invalid provenance source identity'
    assert source.get('encoding') == 'json-sort-keys-utf8-compact'
    assert isinstance(figure.get('provenance'), dict), 'Missing inline provenance payload'
    assert isinstance(figure['provenance'].get('original_figure_id'), str)
    assert re.fullmatch(r'[0-9a-f]{64}', source.get('source_file_sha256', ''))
    assert source.get('merged_from', '').endswith('.provenance.json')
    encoded = json.dumps(figure['provenance'], sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    assert hashlib.sha256(encoded).hexdigest() == source.get('payload_sha256'), 'Provenance payload changed'
    return 1


class TutorialHTMLParser(HTMLParser):
    """Collect real HTML image and anchor attributes without matching raw markup."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'img':
            assert attrs.get('src'), 'HTML images need a source'
            assert attrs.get('alt', '').strip(), 'HTML images need descriptive alt text'
            self.images.append(attrs['src'])
            self.links.append(attrs['src'])
        elif tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])

    handle_startendtag = handle_starttag


def tutorial_assets(text):
    """Collect Markdown and HTML assets, excluding fenced examples and comments."""
    visible = re.sub(r'```.*?```|~~~.*?~~~|<!--.*?-->', '', text, flags=re.S)
    parser = TutorialHTMLParser()
    parser.feed(visible)
    parser.close()
    images = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', visible)
    links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', visible)
    return images + parser.images, links + parser.links


def check_local_links(text, document):
    """Check Markdown links and HTML src/href, ignoring external destinations."""
    _, targets = tutorial_assets(text)
    for target in targets:
        # Markdown permits angle-delimited URLs and an optional quoted title.
        target = target.strip()
        if target.startswith('<'):
            target = target[1:target.index('>')]
        else:
            target = re.split(r'\s+[\"\']', target, maxsplit=1)[0]
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        local = document.parent / unquote(url.path)
        assert local.exists(), (document, target)


def check_tutorial_text(text, case_ids, figure_ids):
    """Keep chapter pages English, concise, and connected to runnable examples."""
    assert not re.search(r'[\u4e00-\u9fff]', text), 'Tutorial pages must be written in English'
    images, _ = tutorial_assets(text)
    assert images, 'Show at least one core result figure'
    assert set(re.findall(r'--case=([A-Za-z0-9_-]+)', text)) <= set(case_ids), 'Unknown calculation case'
    assert set(re.findall(r'--figure=([A-Za-z0-9_-]+)', text)) <= set(figure_ids), 'Unknown figure recipe'
    prose = re.sub(r'```.*?```', '', text, flags=re.S)
    prose = re.sub(r'`[^`]*`', '', prose)
    prose = re.sub(r'\]\([^)]*\)', '](link)', prose)
    assert not re.search(r'(?i)historical|new minus old|f278|migration|sidecar', prose), 'Keep development comparisons out of tutorial prose'
    return len(images)



def check_plot_teaching_labels(config):
    """Reject development narrative in display fields, not immutable source records."""
    display_keys = {'title', 'suptitle', 'label', 'xlabel', 'ylabel', 'text', 'caption'}
    forbidden = r'(?i)historical|new[ _-]+minus[ _-]+old|f278|old[ _-]+tb'
    def walk(value, display=False):
        if isinstance(value, dict):
            for key, item in value.items():
                walk(item, display or key in display_keys)
        elif isinstance(value, list):
            for item in value:
                walk(item, display)
        elif display and isinstance(value, str):
            assert not re.search(r'[\u4e00-\u9fff]', value), 'Plot labels must be English'
            assert not re.search(forbidden, value), 'Keep development comparisons out of teaching figures'
    walk(config)

def main():
    assert not any((ROOT/p).exists()for p in ['migration','validation','Manifest.toml'])
    project=tomllib.loads((ROOT/'Project.toml').read_text());assert 'sources'not in project
    rows=json.loads((ROOT/'manifests/current_inputs.json').read_text())
    assert len(rows)==154 and sum(x['profile']=='reference'for x in rows)==89
    for row in rows:
        p=ROOT/row['input'];assert p.is_file(),p
        data=tomllib.loads(p.read_text());assert isinstance(data['response']['tasks'],dict)
    mapping=json.loads((ROOT/'manifests/reproducibility_map.json').read_text())
    assert mapping['schema']=='tutorial-current-reproduction/4'
    count=0; chapter_figures=[]; chapter_cases=[]
    for chapter in sorted((ROOT/'examples').iterdir()):
        assert not any((chapter/p).exists()for p in ['migration','validation','results','cases','run.jl'])
        assert all((chapter/p).is_file()for p in ['README.md','plot.py','reproduce.json'])
        doc=json.loads((chapter/'reproduce.json').read_text())
        assert doc['schema']=='tutorial-current-case-reproduction/4'
        check_tutorial_text((chapter/'README.md').read_text(), [c['case'] for c in doc['cases']], [f['id'] for f in doc['figures']])
        assert sum(check_inline_provenance(f) for f in doc['figures'])==doc['inline_provenance_count']
        assert not list((chapter/'data').glob('*.provenance.json'))
        chapter_figures.extend(doc['figures'])
        chapter_cases.extend(dict(x,chapter=chapter.name)for x in doc['cases'])
        assert all((ROOT/x['input']).is_file()for x in doc['cases'])
        for case in doc['cases']:
            assert hashlib.sha256((ROOT/case['input']).read_bytes()).hexdigest()==case['input_sha256']
        for fig in doc['figures']:
            count+=1
            for key in ['data','figures','related_current_inputs','model_provenance_files']:
                for rel in fig[key]:assert(ROOT/rel).is_file(),(fig['id'],key,rel)
            source=ROOT/fig.get('recipe',fig.get('script',''))
            assert source.is_file(),source
            if 'recipe'in fig:
                config=json.loads(source.read_text())
                check_plot_teaching_labels(config)
                def paths(v):
                    if isinstance(v,dict):
                        for key,x in v.items():
                            if isinstance(x,str)and x.startswith('../'):
                                assert(source.parent/x).resolve().is_relative_to(ROOT.resolve()),x
                                assert(source.parent/x).is_file(),x
                            else:paths(x)
                    elif isinstance(v,list):
                        for x in v:paths(x)
                paths(config)
    assert count==len(mapping['figures'])
    assert chapter_figures==mapping['figures'] and chapter_cases==mapping['cases']
    for p in ROOT.rglob('*'):
        if p.is_symlink()and'.git'not in p.parts:
            assert p.resolve().is_relative_to(ROOT.resolve())and p.resolve().exists(),p
        if not p.is_file()or'.git'in p.parts or'.runtime'in p.parts:continue
        if p.suffix=='.py':ast.parse(p.read_text())
        if p.resolve()!=Path(__file__).resolve() and p.suffix in ['.py','.jl','.json','.toml','.md','.txt']:
            text=p.read_text();assert not re.search(r'/Users/|/Volumes/|169\.254\.|WannierNLQG-internal|1\.2\.1-dev',text),p
        if p.suffix=='.md':
            check_local_links(p.read_text(), p)
    for name in ['data_inventory.json','figure_inventory.json']:
        inventory=ROOT/'manifests'/name
        if not inventory.exists():continue
        for row in json.loads(inventory.read_text())['files']:
            p=ROOT/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],p
    materials=json.loads((ROOT/'manifests/material_requirements.json').read_text())
    check_material_requirements(rows,materials,tomllib.loads((ROOT/'Materials/paths.example.toml').read_text())['paths'])
    print(f'CURRENT_LAYOUT_PASS chapters=17 inputs=154 selected_recipes={count}')
if __name__=='__main__':main()
