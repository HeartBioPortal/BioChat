from xml.etree import ElementTree
from collections import defaultdict
from itertools import count, zip_longest, dropwhile
from operator import itemgetter
from Bio import Entrez
import numpy as np
import xmltodict
import time
from configDONE import *
import json
import re



class BaseParser:
    """The base class for xml file parsing."""

    def __init__(self, *args, **kwargs):
        self.xml_file_path = kwargs['xml_file_path']
        self.json_file_path = kwargs.get('json_file_path')
        self.citation_file_path = kwargs.get('citation_file_path')

    def create_tree(self):
        """Creat the tree object from xml file."""
    
        with open(self.xml_file_path) as f:
            tree = ElementTree.parse(f)
            root = tree.getroot()
        return root

    def json_creator(self, result):
        """Create a json file from result."""

        with open(self.json_file_path, 'w') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
    
    def extract_citations(self):
        """Extract citations from the end of the guideline file."""

        root = self.create_tree()
        tree = root.iter('text')
        regex1 = re.compile(r'^S\.?\d+[\d,\s.-]+$')
        regex2 = re.compile(r'^(S\d+[\d,\s.-]+)(.*)')
        result = {}
        pre = None
        tree = dropwhile(
            lambda x: ''.join(i.text for i in x.findall('b')).strip().lower() != 'references' and 
            "".join(x.itertext()).strip() != 'R E F E R E N C E S',
            tree,
        )
        for node in tree:
            if node.findall('b') or node.findall('i'):
                continue
            text = "".join(node.itertext()).strip()
            if regex1.match(text):
                result[text.strip('. ')] = ''
                pre = text.strip('. ')
            elif regex2.match(text):
                text, rest = regex2.match(text).groups()
                result[text.strip('. ')] = rest
                pre = text.strip('. ')
            elif pre:
                result[pre] += ' ' + text
        return result
    
    def extract_citations2(self):
        """Extract citations from the end of the guideline file for
        version_2 citation format."""
        root = self.create_tree()
        tree = root.iter('text')
        tree = dropwhile(
            lambda x: 'references' not in {
                "".join(x.itertext()).strip().lower(),
                "".join(i.get('text', '') for i in x.findall('b')).strip().lower()  
                }  and 
            "".join(x.itertext()).strip() != 'R E F E R E N C E S',
            tree,
        )
        regex = re.compile(r'(\d+)\.(.*)')
        result = {}
        temp = ''
        pre = None
        for node in tree:
            text = "".join(node.itertext()).strip()
            if text.startswith('Downloaded from') or node.findall('b'):
                continue
            
            try:
                num, desc = regex.match(text).groups()
            except AttributeError:
                temp += ' ' + text
            else:
                if pre is not None:
                    result[pre] = temp
                pre = num 
                temp = desc.strip()

        return result
    
    def create_json(self):
        """Create the final json file from extracted data."""

        charts = self.extract_charts()
        self.json_creator(charts)

        if self.citation_version == 1:
            citations = self.extract_citations()
        else:
            citations = self.extract_citations2()

        self.json_file_path = self.citation_file_path
        self.json_creator(citations)



class GuidelinesParser(BaseParser):
    """Parsing guideline files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 0
        self.citation_version = kwargs['citation_version']

    def extract_charts(self):
        """Extract data from charts."""
        
        result = defaultdict(dict)
        root = self.create_tree()
        tree = list(root.iter('text'))
        regex = re.compile(r'.*?([S\d,\s.–-]+\d)$')
        # look at triples of nodes (COR, LOE and Recommendations)
        for ind, (node1, node2, node3) in enumerate(zip(tree, tree[1:], tree[2:])):
            try:
                text1 = "".join(node1.itertext()).strip()
                text2 = "".join(node2.itertext()).strip()
                text3 = "".join(node3.itertext()).strip()
                # Chart header
                # if node2.text is None and
                if re.match(r"[Rr]ecommendation(?:s)? for", text2):
                    self.counter += 1
                    result[self.counter]['title'] = text1
                    cc = 0
                    for i in tree[ind+2:]:
                        cc += 1
                        if cc > 5:
                           text2 = None
                           break
                        tx = ' ' + "".join(i.itertext()).strip()
                        if tx in {' COR', ' LOE', ' RECOMMENDATIONS'}:
                            break
                        text2 += tx 
                    if text2 is None:
                        continue 
                    result[self.counter]['sub_title'] = text2
                    result[self.counter]['rows'] = []
                # Filter recommendations based on their COR and LOE
                elif text1 in {'IIa', 'IIb'} and text2 in {'B-R', 'B-NR', 'C-LD'}:
                    tx = ''
                    for i in tree[ind + 3:]:
                        tx = ' ' + "".join(i.itertext()).strip()

                        text3 +=  tx
                        if tx.endswith(').') or regex.match(tx):
                            break
                    result[self.counter]['rows'].append([
                        text1,
                        text2,
                        text3.split(None, 1)[1]
                    ])
            except Exception as exc:
                print("rows exception is here") 
        return result


class GuidelinesParser2(BaseParser):
    """Parsing guideline files with different format."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 0
        self.citation_version = kwargs['citation_version']

    def extract_charts(self):
        """Extract data from charts."""
        
        result = defaultdict(dict)
        root = self.create_tree()
        tree = list(root.iter('text'))
        # look at triples of nodes (COR, LOE and Recommendations)
        for ind, (node1, node2, node3) in enumerate(zip(tree, tree[1:], tree[2:])):
            try:
                text1 = "".join(node1.itertext()).strip()
                text2 = "".join(node2.itertext()).strip()
                text3 = "".join(node3.itertext()).strip()
                # Chart header
                if "recommendations for" in text2.lower() or "recommendation for" in text2.lower():
                    self.counter += 1
                    result[self.counter]['title'] = text2
                    result[self.counter]['sub_title'] = text3
                    result[self.counter]['rows'] = []
                # Filter recommendations based on their COR and LOE
                elif text1 in {'IIa', 'IIb'} and text2 in {'B-R', 'B-NR', 'C-LD'}:
                    tx = ''
                    for i in tree[ind + 3:]:
                        tx = "".join(i.itertext()).strip()
                        if tx != '.':
                            tx = ' ' + tx 
                        text3 +=  tx
                        if text3.endswith(').'):
                            break
                    result[self.counter]['rows'].append([
                        text1,
                        text2,
                        text3.split(None, 1)[1]
                    ])
            except Exception as exc:
                print(exc)
        return result


class GuidelinesParser3(BaseParser):
    """Parsing guideline files with different format."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.counter = 0
        self.citation_version = kwargs['citation_version']
        self.title_font = kwargs['title_font']
        self.subtitle_font = kwargs['subtitle_font']
        self.class_font = kwargs['class_font']

    def extract_charts(self):
        """Extract data from charts."""
        
        result = defaultdict(dict)
        root = self.create_tree()
        tree = root.iter('text')
        class_regex = re.compile(r'^CLASS .{1,4}$')
        title_regex = re.compile(r'\d*\.[\d.]+.*')
        counter = 0
        d = {}
        title = subtitle = ''
        while True:
            try:
                node = next(tree)
            except StopIteration:
                break
            else:
                font = int(node.get('font'))
                text = "".join(node.itertext()).strip()
            if font in self.title_font and title_regex.match(text):
                temp_counter = 0
                title += text
                while True:
                    if 'recommendation' in text.lower():
                        counter += 1
                        d[counter] = defaultdict(list)
                        d[counter]['title'] = title
                        title = ''
                        break
                    elif temp_counter > 4:
                        title = ''
                        break
                    temp_counter += 1
                    node = next(tree)
                    text = "".join(node.itertext()).strip()
                    title += text
                continue
            
            elif counter in d and font == self.subtitle_font:                   
                subtitle += ' ' + text                
            
            elif subtitle:
                d[counter]['subtitle'] = subtitle
                subtitle = ''
            
            elif class_regex.match(text):
                clss = text
                recom = ''
                while True:
                    node = next(tree)
                    font = int(node.get('font'))
                    text = "".join(node.itertext()).strip()
                    if font == self.class_font:
                        recom += text
                    else:
                        d[counter][clss].append(recom)
                        break
        return d


class DataSupParser(BaseParser):
    """Parse data supplement files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The required regex for extracting acronym, author and year.
        self.ref_open = False
        self.version = kwargs['version']
        self.left_down = kwargs['left_down']
        self.left_up = kwargs['left_up']
        self.left_down_2 = kwargs.get('left_down_2', 0)
        self.left_up_2 = kwargs.get('left_up_2', 0)
        self.RFG = kwargs['row_filed_gap']
        self.aay_regex = re.compile(
                r'^([\w\s,-]+(?:et al\.)?)?\W+(\d{4})?.*(?:\(\d+\))?\W+(\d+)\W*'
            )

    def add_if_found_col(self, d, left, text, width):
        """Add the text to the corresponding key if it found one
        otherwise create a new key."""
        try:
            candidate_key = next(i for i in d if i - self.RFG < left < i + self.RFG)  
        except StopIteration:
            d[left] = {'text':text, 'width':width, 'left': left}
        else:
            d[candidate_key]['text'] += ' ' + text
            d[candidate_key]['width'] = max(d[candidate_key]['width'], width)

        return d
    
    def add_if_found(self, d, left, text, titles, RFG=None):
        """Add the text to the corresponding key if it found one
        otherwise create a new key."""
        if RFG is None:
            RFG = self.RFG              

        # try:
        #     candidate_key = next(i for i in d['data'] if left - RFG < i < left + RFG)
        # except StopIteration:
        #     d['data'][left] = text
        # else:
        #     d['data'][candidate_key] += ' ' + text
        # finally:
        d['data'].append((text, left))
        d['titles'] |= titles
        return d

    def extract_data_sup(self): 
        """Extract data from charts."""

        root = self.create_tree()
        tree = root.iter('text')
        result = {}
        d = {'data':[], 'titles':set(), 'references': []}     
        s = 0
        pre = 0
        # loop over the nodes
        num_regex = re.compile(r'\(\d+\)')  
        while True:
            try:
                node = next(tree)
            except StopIteration:
                break
            # get the left attribute of the node.
            left = int(node.get('left'))
            # titles are bold phrases on each section followed by colon.
            titles = {i.text.strip(' :') for i in node.findall('b') if i.text and i.text.strip()}  
            # iterate through all sub tags and join the texts together.
            text = "".join(node.itertext()).strip().replace('\u2013', '-')
            if not text:
                d['titles'] |= titles
                continue
            
            if node.findall('b') and text.startswith('Data Supplement'):    
                cols = {}
                while True:
                    node = next(tree)
                    left = int(node.get('left'))
                    width = int(node.get('width'))
                    if node.findall('b'):
                        col = ''.join([i.text for i in node.findall('b')])
                        cols = self.add_if_found_col(cols, left, col, width)
                    else:
                        text = "".join(node.itertext()).strip().replace('\u2013', '-')
                        break
                cols = sorted(cols.items(), key=itemgetter(0))
                cols = [(j['text'].strip().replace(' ', '_'), j['width'], j['left']) for i, j in cols if j['text'].strip()]
            # these lines have same left as starting nodes but they're out of
            # table so we ignore them.
            try:
                cols
            except:
                continue
            
            #if ("Search Terms" in text) or ("Date of Search" in text) or text.startswith('Study'):
                #print("this is in search terms or study")
            #    continue

            # We detect the start of a new block or row of the table if the left
            # is between 80 and 100
            #if self.left_down < left < self.left_up or self.left_down_2 < left < self.left_up_2:
            if left < 100:
                # filter noises
                if self.version == 3:
                    tpp = text.strip('() ,')
                    if tpp.isdigit():
                        d['references'] += [tpp]
                        continue
                    self.ref_open = True
                if 3 < len(text) < 40:
                    # if the previous node has also been a starting node
                    # this means that we're dealing with a multiline starting
                    # node
                    if left - 20 < pre < left + 20:
                        d = self.add_if_found(d, left, text, titles)
                    else:
                        d['cols'] = cols
                        result[s] = d
                        d = {'data': [(text, left)], 'titles':titles, 'references': []}
                        s += 1
                else:
                    continue
            # if we're not at a starting node we should add the node to the 
            # dictionary.
            elif left > self.left_up:
                if self.version == 3 and self.ref_open: 
                    ref = self.check_if_reference(text)
                    if ref:
                        d['references'] += [i for i in ref if i] 
                elif len(text) < 100: 
                    d = self.add_if_found(d, left, text, titles)
            pre = left
            pre_text = text
        return result

    def pre_clean(self, result):
        final = {}
        for key, value in result.items():
            cols = value['cols'][:]
            data = value['data'][:]
            if len(cols) == 0:
                cols = [('Not available', 0, 0)]
            cols, widths, _ = zip(*cols)
            cols = ('acronym_author_year',) + cols[1:]
            final[key] = {
                'data': {},
                'titles':value['titles'],
                'references': value['references'],
                'cols': cols
            }
            try:
                texts, lefts = zip(*data)
            except ValueError:             
                continue
            
            #initializing count
            sp = []
            former_left = lefts[0]
            count = 0
            for i in range(len(lefts)):
                if lefts[i] <= former_left + 45: #45 accounts for the bullet points
                    count += 1
                else:
                    sp.append(count)
                    count += 1
                    former_left = lefts[i]

            #widths = np.array(widths)
            #interval = int(widths.mean() - 5)
            #sp = np.where(np.diff(lefts) > interval)[0] + 1     
            splitted = np.split(texts, sp)
            final[key]['data'] = [' '.join(sub) for sub in splitted]
        return final

    
    def check_if_reference(self, text):
        """In version 3 data sups the parenthesis is, in 95% of the time,
        separately in a `text` tag and in 5% at the end of another tag."""
        if text == ')':
            self.ref_open = False
            return False
        elif text.endswith(')'):
            self.ref_open = False
            return text.strip(' ())').split(',')
        elif re.match(r'[(),\d\s]+', text):
            return text.strip('() ').split(',')
    
    def extract_references(self):
        base_parser = BaseParser(xml_file_path=self.xml_file_path)
        return base_parser.extract_citations2()

    def clean_sup_dict(self, result):
        """Add proper keys to the dict, remove noisy data and
        categorize the content."""

        cits = self.extract_references()
        # remove empty items and fix endpoint titles
        tmp = {
            k : {'data':[
                i for i in v['data'] if i.strip()
            ], 'titles': [
                        i + '° ' + 'endpoint' if i.isdigit() else i 
                            for i in (v['titles'] - {'endpoint'})
                        ],
                'references': [cits.get(i) for i in v.get('references')],
                'cols':v['cols']} for k,v in result.items() 
        }
        final = {}
        # use proper keys for table fields based on the number of fields
        for key,value in tmp.items():
            if self.version != 4:
                if len(value['data']) == 5:
                    if self.version == 1:
                        data = dict(zip(BASIC_KEYS_5, value['data']))   
                    else:
                        data = dict(zip(BASIC_KEYS_5_3, value['data']))
                elif len(value['data']) == 6:
                    if self.version == 1:
                        data = dict(zip(BASIC_KEYS_6, value['data']))
                    else:
                        data = dict(zip(BASIC_KEYS_6_2, value['data']))
                elif len(value['data']) == 7:
                    if self.version == 1:
                        data = dict(zip(BASIC_KEYS_7, value['data']))
                    else:
                        data = dict(zip(BASIC_KEYS_7_2, value['data']))
                elif len(value['data']) == 8:
                    data = dict(zip(BASIC_KEYS_8, value['data']))
                elif len(value['data']) == 11:
                    data = dict(zip(BASIC_KEYS_11, value['data']))
                elif len(value['data']) == 13:
                    data = dict(zip(BASIC_KEYS_13, value['data']))
                elif len(value['data']) == 14:
                    data = dict(zip(BASIC_KEYS_14, value['data']))
                else:
                    continue
            else:
                data = dict(zip(value['cols'], value['data']))
            try:
                aay = data.pop('acronym_author_year').replace('●', '')
            except:
                print("Key Error: acronym_author_year")
                pmid = 0
                cleaned = {}
            else:
                regex = re.compile(
                    r'{}\s*'.format(r'|'.join([
                        re.escape(i) for i in value['titles'] if i in aay and len(i)>1]))
                    )
                # remove noisy strings 
                acr = re.sub(
                    r'Study\s?Acronym\s?;|\s?Author\s?;|\s?Year\s?Published',
                    '',
                    ' '.join([i.strip() for i in regex.findall(aay)])).strip()
                if not acr:
                    acr = None
                else:
                    aay = aay.replace(acr, '').strip()
                try:
                    author, year, pmid = self.aay_regex.search(aay).groups()
                except AttributeError as exc:
                    print(exc, aay)
                    continue
                cleaned = {'acronym': acr,'author': author, 'year': year}
            regex = re.compile(r'({})\s*:'.format(r'|'.join([re.escape(i) for i in value['titles']])))           
            d = defaultdict(str)

            # categorize the content of each row in chart based on the bold titles
            split_regex = re.compile(r'\u25cf|\u2022')

            for k, v in data.items():
                sp = regex.split(v)
                if len(sp) == 1:
                    d[k] = [i for i in split_regex.split(sp[0].strip()) if i.strip()]
                    continue
                while True:
                    try:
                        item = split_regex.sub('', sp.pop(0))
                    except (IndexError, re.error) as exc:
                        break
                    else:
                        if not item.strip():
                            continue
                        if item in value['titles']:
                            try:
                                d[item] = split_regex.sub('', sp.pop(0)).strip()
                            except IndexError:
                                d[item] = ''
                        else:
                            d[k] += item
            cleaned.update(d)
            if self.version == 3:
                cleaned['references'] = value['references']
            else:
                cleaned['pmid'] = pmid
            yield cleaned
    
    def create_json(self):
        """Create the final json file."""

        result = list(
            self.clean_sup_dict(
                self.pre_clean(
                    self.extract_data_sup()
                    )
                )
            )
        # result = {k: {i:list(j) if isinstance(j, set) else j 
        #         for i,j in v.items()} for k,v in self.extract_data_sup().items()}
        self.json_creator(result)


class Merge:
    """Merge guidelines with its respective supplemented data."""

    def __init__(self, *args, **kwargs):
        self.json_file_name = kwargs['json_file_name']
        self.guidelines_path = kwargs['guidelines_path']
        self.data_supplements_path = kwargs['data_supplements_path']
        self.citations_path = kwargs['citations_path']
        self.citation_version = kwargs['citation_version']

    def load_guidelines(self):
        """Read guidelines json file."""

        return self.read_json(
            self.guidelines_path
        )
    
    def load_data_supplements(self):
        """Read data supplement json file."""

        return self.read_json(
            self.data_supplements_path
        )
    
    def load_citations(self):
        """Load citations json file."""
        
        return self.read_json(
            self.citations_path
        )
    
    def read_json(self, path):
        """Load a json file."""

        with open(path) as f:
            return json.load(f)

    def run(self):
        guidelines = self.load_guidelines()
        datasup = self.load_data_supplements()
        citations = self.load_citations()
        final_result = {}
        if self.citation_version == 1:
            cit_regex = re.compile(r'\(?([S\d–,\s.-]+)(?:[\).\s]+)?$')
        else:
            cit_regex = re.compile(r'\(?([\d–,\s]+)(?:[\).\s]+)?$')
        for key, value in guidelines.items():
            try:
                value['rows']
            except KeyError:
                # corrupted guideline
                continue
            for row in value['rows']:
                temp_data = {}
                recom = row[-1]
                try:
                    cit_string = cit_regex.search(recom).group(1).strip(' .')
                except Exception as exc:
                    print(recom, exc)
                    continue

                for cit in self.parse_citation(cit_string):
                    try:
                        pmids = self.find_PMID(
                            citations[cit.strip()]
                        )
                    except KeyError:
                        print("ERROR! ", cit.strip(), "Is missing.")
                        continue
                    print(cit)
                    for p in pmids:
                        try:
                            d = [i for i in datasup if i['pmid'] == p]
                            if len(d) == 1:
                                res = d[0]
                            else:
                                res = defaultdict(set)
                                for i in d:
                                    for j,k in i.items():
                                            res[j].add(tuple(k) if isinstance(k, list) else k)
                                res = {k:v.pop() if len(v) == 1 else list(v) for k,v in res.items()}
                            temp_data[p] = res
                        except KeyError as exc:
                            print("Key Error:", exc)
                        else:
                            break
                temp_data = {k: self.find_abstract(k) if not v else v for k, v in temp_data.items()}
                row.append(temp_data)
            final_result[key] = value
        return final_result

    def parse_citation(self, cit_string):
        sp = [i.split('\u2013') for i in cit_string.strip('() ').split(',')]
        for cit in sp:
            if len(cit) == 2:
                if self.citation_version == 1:
                    base, start = cit[0].split('-')
                    start = int(start.strip())
                    end = int(cit[1].split('-')[-1].strip())
                    for i in range(start, end + 1):
                        yield f"{base.strip()}-{i}"
                else:
                    start, end = map(int, cit)
                    for i in range(start, end + 1):
                        yield f"{i}"
            else:
                yield cit[0].replace(' ', '')

    def find_PMID(self, citation_info):
        """Find the PMID using PubMed's API."""

        years = re.findall(r'\W(\d{4})\W', citation_info)
        # q = ','.join(citation_info.split(',')[:2] + [f'({i})' for i in years])
        q = re.sub(r'[.;]', '|', citation_info)
        Entrez.email = 'test@example.com'
        try:
            handle = Entrez.esearch(db='pubmed',                                                                                             
                                    sort='relevance',                                                                                        
                                    retmax='3',
                                    retmode='xml', 
                                    term=q)
            results = Entrez.read(handle)
        except TimeoutError:
            return
        try:
            return results['IdList']
        except IndexError as exc:
            print(exc, 'query: ', q)
    
    def find_abstract(self, pmid):
        """Find the abstract of the papers which don't have any data supplement."""

        Entrez.email = 'test@example.com'
        handle = Entrez.efetch(db='pubmed', id=pmid, rettype="gb", retmode="xml")
        f = handle.read()
        try:
            res = xmltodict.parse(f)
            cit = res['PubmedArticleSet']['PubmedArticle']['MedlineCitation']
            title = cit['Article']['ArticleTitle']
            abc = cit['Article']['Abstract']['AbstractText']
            if isinstance(abc, str):
                abstract = abc
            else:
                abstract = '\n'.join([i if isinstance(i, str) else i['#text'] for i in abc])
            authors = [i.get('LastName','') + ' ' + i.get('ForeName', '') for i in cit['Article']['AuthorList']['Author']]
            result = {
                'title': title,
                'authors': ', '.join(authors),
                'abstract': abstract
            }
        except Exception as exc:
            print(str(exc)[:50])
            # raise Exception('Probably KeyError').with_traceback(e.__traceback__)
            handle = Entrez.efetch(db='pubmed', id=pmid, rettype="gb", retmode="text")
            return handle.read()
        else:
            return result

    def create_json(self):
        """Create the final json file."""

        result = self.run()
        with open(self.json_file_name, 'w') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)






if __name__ == '__main__':

    for item in SCRAPING[0:1]:
        directory = item['directory']
        guideline_xml = item['guideline_xml']
        datasup_xml = item['datasup_xml']
        cit_version = item['cit_version']
        left_down = item['left_down']
        left_up = item['left_up']
        dsup_version = item['dsup_version']
        guideline_version = item['guideline_version']
        row_filed_gap = item['row_filed_gap']
        left_down_2 = item.get('left_down_2', 0)
        left_up_2 = item.get('left_up_2', 0)
        title_font = item.get('title_font', 0)
        subtitle_font = item.get('subtitle_font', 0)
        class_font = item.get('class_font', 0)
        print(directory)

        if guideline_version == 1:
            GP = GuidelinesParser
        elif guideline_version == 2:
            GP = GuidelinesParser2
        else:
            GP = GuidelinesParser3

        p = GP(
            xml_file_path=f'{directory}/{guideline_xml}',
            json_file_path=f'{directory}/guidelines.json',
            citation_file_path=f'{directory}/citations.json',
            citation_version=cit_version,
            title_font=title_font,
            subtitle_font=subtitle_font,
            class_font=class_font)
        p.create_json()

        p = DataSupParser(
            xml_file_path=f'{directory}/{datasup_xml}',
            json_file_path=f'{directory}/datasup.json',
            left_down=left_down,
            left_up=left_up,
            left_down_2=left_down_2,
            left_up_2=left_up_2,
            version=dsup_version,
            row_filed_gap=row_filed_gap)
        p.create_json()

        # M = Merge(
        #     json_file_name=f'{directory}/merged_result.json',
        #     data_supplements_path=f'{directory}/datasup.json',
        #     guidelines_path=f'{directory}/guidelines.json',
        #     citations_path=f'{directory}/citations.json',
        #     citation_version=cit_version,
        # )
        # M.create_json()
        # time.sleep(3)