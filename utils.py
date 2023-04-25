from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm
import warnings
import os
from datetime import datetime as dt
import pandas as pd


def load_celegans(keywords, sep):
    print(f'{dt.now()} - Querying celegans dataset withthe following features : {keywords}.')
    queries = queries_from_features(keywords)
    query_db(queries, sep)
    return 'query_result.txt'

def load_pgr(keywords, sep):
    feature_type = {
        "pgr-gene-pheno" : "bipartite",
        "pgr-gene-gene" : "gene",
        "pgr-gene-disease" : "bipartite",
        "pgr-pheno-pheno" : "phenotype",
        "pgr-disease-disease" : "phenotype",
    }

    for keyword in keywords:
        # Retrieve data files
        load_celegans([keyword], sep)
        with open('query_result.txt', 'r') as f:
            lines = f.readlines()
        with open(f'{keyword}.txt', 'a') as f:
            f.write(f'from{sep}to{sep}weight\n')
            for line in lines:
                parsed = line.split(sep)
                parsed = parsed[0] + sep + parsed[2].strip('\n') + sep + '1.000\n'
                f.write(parsed)
        os.remove('query_result.txt')

    # Create input file
    with open('input.txt', 'a') as f:
        f.write(f'type{sep}file_name\n')
        for keyword in keywords:
            f.write(f'{feature_type[keyword]}{sep}{keyword}.txt\n')
    return 'input.txt'

def load_by_query(query):
    query = add_prefixes(query)
    query_db([query])

def query_db(queries, sep):
    """Queries the database with a SPARQL query that returns a graph (ie uses a CONSTRUCT clause)."""
    # Set up the SPARQL endpoint
    sparql = SPARQLWrapper("http://cedre-14a.med.univ-rennes1.fr:3030/WS286_2023march08_RDF/sparql")
    warnings.filterwarnings("ignore")
    for query in tqdm(queries, desc="Querying SPARQL endpoint..."):

        # Set the query
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        # Execute the query and parse the response
        results = sparql.query()
        results = results.convert()
        # Store the constructed subgraph
        try:
            with open('query_result.txt', 'a') as f:
                for s, p, o in results:
                    if any(x.toPython() == '' for x in (s, p, o)): # Checks if the triple is complete
                        continue
                    f.write(f'{s}{sep}{p}{sep}{o}\n')       
        except:
            raise Exception("Check that the query output is a triple like ?s ?p ?o. Reminder: You must use a CONSTRUCT query")
    print(f'{dt.now()} - Query executed !')

def queries_from_features(keywords):
    features = {       
        "gene" : # This include not only genes but also their products, ie proteins, miRNAs, etc.
            """
            CONSTRUCT {
                ?geneid rdf:type ?type .
                ?geneid rdf:label ?lab .
            }
            WHERE {
                ?geneid rdf:type ?type .
                ?geneid rdfs:label ?lab .
                FILTER (
                    ?type = sio:000985 || #protein coding gene
                    ?type = sio:010035 || # gene
                    ?type = sio:000988 || # pseudogene
                    ?type = sio:001230 || # tRNA gene
                    ?type = sio:000790 || # non coding RNA gene (includes ncRNA, miRNA, linc RNA, piRNA, antisense lncRNA)
                    ?type = sio:001182 || # rRNA gene
                    ?type = sio:001227 || # scRNA gene
                    ?type = sio:001228 || # snRNA gene
                    ?type = sio:001229    # snoRNA gene
                )
            }
            """,

        "phenotype" : # Phenotypes associated to gene and gene products
           """
            CONSTRUCT {
                ?wbpheno nt:001 ?geneid .
                ?wbpheno ?rel ?pheno .
            }
            WHERE {
                ?wbpheno nt:001 ?geneid .
                ?wbpheno ?rel ?pheno .
                FILTER(?rel = sio:000281|| ?rel = sio:001279)
                ?wbpheno sio:000772 ?eco .
  				FILTER (REGEX(STR(?pheno), "^" + STR(wbpheno:))) # Exclude go: annotations
            }
            """,

        "interaction" : # Denotes a physical interaction between genes and gene products.
           """
            CONSTRUCT {
                ?wbinter nt:001 ?geneid1 .
                ?wbinter nt:001 ?geneid2 .
                ?wbinter  sio:000628 ?interaction_type
            }
            WHERE {
                ?wbinter nt:001 ?geneid1 .
                ?wbinter nt:001 ?geneid2 .
                ?wbinter rdf:type ?rel .
 				?wbinter  sio:000628 ?interaction_type .
                FILTER (?geneid1 != ?geneid2)
            }
            """,

        "disease" : # diseases related to celegans genes and gene products
           """
            CONSTRUCT {    
               ?wbdisease nt:001 ?geneid .
               ?wbdisease nt:009 ?doid .
            }
            WHERE {
              ?wbdisease nt:001 ?geneid .
              ?wbdisease nt:009 ?doid . # refers to disease associated with celegans gene
              FILTER NOT EXISTS{ ?wbdisease sio:000772 <http://purl.obolibrary.org/obo/ECO_0000201>. }  # without ortholog
            }
            """,

          "disease_plus_ortho" : # orthologous diseases (eg. human) related to celegans genes and gene products
           """
            CONSTRUCT {    
               ?wbdisease nt:001 ?geneid .
               ?wbdisease nt:009 ?doid .
            }
            WHERE {
              ?wbdisease nt:001 ?geneid .
              ?wbdisease nt:009 ?doid . # refers to disease associated with celegans gene
            }
            """,

        "expression_value" : # /!\ Gene expression values. Very large amount of data, quite likely to be noise /!\
           """
            CONSTRUCT {
                ?wbexpr_val nt:001 ?geneid .
                ?wbexpr_val sio:000300 ?expr_value .
                ?wbexpr_val nt:002 ?lifestage .                
            }
            WHERE {
                ?wbexpr_val nt:001 ?geneid .
                ?wbexpr_val sio:000300 ?expr_value .
                ?wbexpr_val nt:002 ?lifestage .
            }
            """,

        "expression_pattern" : # Gene expression patterns (ie. location in c elegans)
           """
            CONSTRUCT {                
                ?wbexpr_pat nt:001 ?geneid .
                ?wbexpr_pat nt:004 ?expr_id .
                ?wbexpr_pat nt:002 ?wblifestage .
                
            }
            WHERE {
                ?wbexpr_pat nt:001 ?geneid .
                ?wbexpr_pat nt:004 ?expr_id .
                ?wbexpr_pat nt:002 ?wblifestage .
                
            }
            """,
        "lifestage-ontology" : # Structures expression_pattern nodes
            """
            CONSTRUCT {
            ?node1 rdfs:subClassOf ?node2 .
            }
            WHERE {
            ?node1 rdfs:subClassOf ?node2 .
            FILTER REGEX( STR(?node1), "https://wormbase.org/search/life_stage")
            FILTER REGEX( STR(?node2), "https://wormbase.org/search/life_stage")
            }
            """,

        "disease-ontology" : # Structures disease nodes
            """
            CONSTRUCT {
            ?disease rdfs:subClassOf ?disease2 .
            }
            WHERE {
            ?disease rdfs:subClassOf ?disease2 .
            FILTER REGEX( STR(?disease), "id=DOID:")
            FILTER REGEX( STR(?disease2), "id=DOID:")
}
            """,
            
        "phenotype-ontology" : # Structures phenotype nodes
            """
            CONSTRUCT {
            ?node1 rdfs:subClassOf ?node2 .
            }
            WHERE {
            ?node1 rdfs:subClassOf ?node2 .
            FILTER REGEX( STR(?node1), "https://wormbase.org/species/all/phenotype/WBPhenotype:")
            FILTER REGEX( STR(?node2), "https://wormbase.org/species/all/phenotype/WBPhenotype:")
            }
            """,

        "go-annotation" : # Gene Ontology annotations
            """
            CONSTRUCT {
            ?wbdata ?linktype ?goid .
            }
            WHERE {
            ?wbdata ?linktype ?goid .
            FILTER (REGEX(STR(?goid), "^" + STR(go:)))
            FILTER (
                ?linktype = ro:0002327 || # enables
                ?linktype = ro:0001025 || # located_in
                ?linktype = sio:000068 || # part_of
                ?linktype = ro:0002331 || # involved_in
                ?linktype = sio:001403 # is associated with
            )
            }
            """,

        "go-ontology" :  # Structures go nodes
            """
            CONSTRUCT {
            ?node1 rdfs:subClassOf ?node2 .
            }
            WHERE {
            ?node1 rdfs:subClassOf ?node2 .
            FILTER REGEX( STR(?node1), "http://amigo.geneontology.org/amigo/term/GO:")
            FILTER REGEX( STR(?node2), "http://amigo.geneontology.org/amigo/term/GO:")
            }
            """,

        "toy-example" : # A toy example to test the pipeline
            """
            CONSTRUCT {
                ?wbdata nt:001 ?gene .
                ?gene rdf:type ?type .
                ?wbdata sio:001279 ?allpheno . 
            }
            WHERE {
                ?wbdata nt:001 ?gene .
                ?gene rdf:type ?type .
                ?wbdata sio:001279 ?allpheno.
  				?allpheno rdfs:subClassOf* ?pheno
            FILTER ( ?pheno = <https://wormbase.org/species/all/phenotype/WBPhenotype:0000601>)
            FILTER (
                ?type = sio:000985 || #protein coding gene
                ?type = sio:010035 || # gene
                ?type = sio:000988 || # pseudogene
                ?type = sio:001230 || # tRNA gene
                ?type = sio:000790 || # non coding RNA gene (includes ncRNA, miRNA, linc RNA, piRNA, antisense lncRNA)
                ?type = sio:001182 || # rRNA gene
                ?type = sio:001227 || # scRNA gene
                ?type = sio:001228 || # snRNA gene
                ?type = sio:001229    # snoRNA gene
            )            
            }
            """
    }
    
    ret = []
    for keyword in keywords:
        if keyword not in features.keys():
            raise Exception("Unknown keyword: " + keyword)
        ret.append(add_prefixes(features[keyword]))
    return ret

def add_prefixes(query):
    prefixes = """
        PREFIX bfo: <http://purl.obolibrary.org/obo/BFO_>
        PREFIX dcterms: <http://purl.org/dc/terms/#>
        PREFIX doid: <https://disease-ontology.org/?id=DOID:>
        PREFIX eco: <http://purl.obolibrary.org/obo/ECO_>
        PREFIX pmid: <https://pubmed.ncbi.nlm.nih.gov/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX ro: <http://purl.obolibrary.org/obo/RO_>
        PREFIX sio: <http://semanticscience.org/resource/SIO_>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        PREFIX ChEBI: <https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:>
        PREFIX EC: <https://enzyme.expasy.org/EC/>
        PREFIX InterPro: <https://www.ebi.ac.uk/interpro/search/text/>
        PREFIX go: <http://amigo.geneontology.org/amigo/term/GO:>
        PREFIX goref: <https://www.pombase.org/reference/GO_REF:> 
        PREFIX omim: <https://www.omim.org/entry/>
        PREFIX taxon: <http://purl.uniprot.org/taxonomy/>
        PREFIX UniPathway: <https://www.unipathway.org>
        PREFIX UniProtKB: <https://www.uniprot.org/uniprot/>
        PREFIX UniProtKB-KW: <https://www.uniprot.org/keywords/>
        PREFIX UniProtKB-SubCell: <https://www.uniprot.org/locations/>
        PREFIX UniRule: <https://www.uniprot.org/unirule/>
        PREFIX wbbt: <https://wormbase.org/species/all/anatomy_term/WBbt:>
        PREFIX wbdata: <https://wormbase.org/wbdata/>
        PREFIX wbexp: <https://wormbase.org/species/all/expr_pattern/Expr>
        PREFIX wbgene: <https://wormbase.org/species/c_elegans/gene/WBGene>
        PREFIX wbgtype: <https://wormbase.org/species/c_elegans/genotype/WBGenotype>
        PREFIX wbinter: <https://wormbase.org/wbinter/>
        PREFIX wbls: <https://wormbase.org/search/life_stage/>
        PREFIX wbperson: <https://wormbase.org/resources/person/WBPerson>
        PREFIX wbpheno: <https://wormbase.org/species/all/phenotype/WBPhenotype:>
        PREFIX wbref: <https://wormbase.org/resources/paper/WBPaper>
        PREFIX wbrnai: <https://wormbase.org/species/c_elegans/rnai/WBRNAi>
        PREFIX wbstrain: <https://wormbase.org/species/c_elegans/strain/WBStrain>
        PREFIX wbtransg: <https://wormbase.org/species/c_elegans/transgene/WBTransgene>
        PREFIX wbvar: <https://wormbase.org/species/c_elegans/variation/WBVar>
        PREFIX wbversion: <https://wormbase.org/about/wormbase_release_>
        PREFIX CGD: <http://www.candidagenome.org/cgi-bin/locus.pl?dbid=>
        PREFIX dictyBase: <http://dictybase.org/gene/>
        PREFIX FB: <https://flybase.org/reports/>
        PREFIX FLYBASE: <https://flybase.org/reports/>
        PREFIX HGNC: <https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:>
        PREFIX MGI: <http://www.informatics.jax.org/marker/>
        PREFIX PANTHER: <http://pantherdb.org/>
        PREFIX PomBase: <https://www.pombase.org/gene/>
        PREFIX RGD: <https://rgd.mcw.edu/rgdweb/report/gene/main.html?id=>
        PREFIX RHEA: <https://www.rhea-db.org/rhea/>
        PREFIX SGD: <https://www.yeastgenome.org/locus/>
        PREFIX TAIR: <https://www.arabidopsis.org/servlets/TairObject?accession=locus:>
        PREFIX ZFIN: <https://www.zfin.org/>
        PREFIX nt: <http://www.semanticweb.org/needed-terms#>"""

    return f"{prefixes}\n{query}"

if __name__ == "__main__":
    # Change directory to the current file path
    current_file_path = os.path.realpath(__file__)
    current_dir = os.path.dirname(current_file_path)
    os.chdir(current_dir)

    if os.path.exists("query_result.txt") == True:
        os.remove("query_result.txt")

    keywords = ['gene', 'phenotype', 'interaction', 'disease_plus_ortho',
     'disease-ontology', 'phenotype-ontology', 'expression_pattern',
      'lifestage-ontology', 'go-ontology', 'go-annotation']
    load_celegans(keywords, sep=' ')