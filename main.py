import argparse
from utils import *
import os

def main():
    '''Parse the command line arguments'''
    parser = argparse.ArgumentParser()

    # General arguments
    parser.add_argument('--keywords', nargs='*', default=None, help='Multiple keywords')
    parser.add_argument('--method', required=True, help='Name of the method')
    parser.add_argument('--dataset', required=True, help='Name of the dataset')
    parser.add_argument('--query', default=None, help='A SPARQL query')
    parser.add_argument('--data_format', default=None, help='Format of the dataset')
    parser.add_argument('--ouput', default='./', help='Directory to store the data')

    #AnyBURL specific arguments
    parser.add_argument('--mem', default=4, help='Memory to use (GB)')
    
    args = parser.parse_args()

    # Change directory
    current_file_path = os.path.realpath(__file__)
    current_dir = os.path.dirname(current_file_path)
    os.chdir(current_dir)

    if args.query:
        load_by_query(args.query)
    elif args.dataset:
        match args.dataset:
            case "celegans":
                load_celegans(args.keywords)
                dataset = "query_result.txt"
            case "ogb_biokg":
                pass
                #data_biokg = load_biokg(args.keywords)
            case "toy-example":
                dataset = "toy-example.txt"
            case _:
                raise Exception("Dataset not supported.")
    else:
        raise Exception("No dataset or query provided.")


    train_model(args.method, dataset)
    if dataset != 'toy-example.txt':
        os.remove(dataset) 

def train_model(method, dataset):
    if method in ["TransE", "TransH", "TransR", "TransD", "TorusE", "RESCAL", "DistMult", "HolE", "ComplEx", "ANALOGY", "ConvKB"]:
        import methods.TorchKGE.kge as kge
        kge.train(method, dataset)
    elif method == "MultiVERSE":
        pass
    elif method == "PhenoGeneRanker":
        pass
    elif method == "DeepPheno":
        pass
    elif method == "MHGCN":
        pass
    elif method == "HybridGNN":
        pass
    elif method == "AnyBURL":
        import subprocess

        # Check data file validity
        with open(dataset, 'r') as f:
            lines = f.readlines()
            for line in lines:
                if not str.isalpha(line[0]):
                    raise Exception("AnyBURL expects that each identifier that appears in the data file starts with a alphabetic character and consists of at least 2 letters.")
        
        # Add training path to config file
        with open('AnyBURL/config-learn.properties', 'a') as f:
            lines = f.readlines()
            f.write(f'PATH_TRAINING = {dataset}')
        
        # Remove the changes made to the config file
        with open('AnyBURL/config-learn.properties', 'w') as f:
            f.write(lines)

    elif method == "GraphLP":
        pass


if __name__ == "__main__":
    main()