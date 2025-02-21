from alpaka.funcs import achat, apull, chat, pull
from arkitekt_next import easy, progress, register
from kraph.api.schema import Graph, GraphView, acreate_graph_view, aget_ontology, acreate_graph_query, Ontology, GraphQuery,  create_graph_query, ViewKind


model = "qwen2.5:7b"


def ontology_to_layout(ontology: Ontology) -> str:
    
    starter = """
    Here are the nodes that you can use:
    
    First the generic nodes, these are nodes that are used to describe the biological
    entities.
    These nodes do not contain any attributes, so the only ways to distinguish them
    is by their name and the edges that point towards them.
    
    
    The list follows the format "AGE_NAME: Name - Short description":
    """
    
    for node in ontology.generic_categories:
        starter += f"{node.age_name}: {node.label} - {node.description}\n"
       
    starter += """
    Then the structure nodes, these are nodes that are are datapoitns where the biological
    data has been measured or observed, the list follows the format "AGE_NAME: Name - Short description":
    Structures do not contain any values, but they are often the origin for measurmeents
    edges that point toward the generic nodes.
    """   
        
    for node in ontology.structure_categories:
        starter += f"{node.age_name}: {node.label} - {node.description}\n"
        
        
        
        
    starter += """
    Next are the relation edges, which describe the connections between different entities.
    They help in understanding how various biological entities interact with one another.
    The list follows the format "AGE_NAME: Name - Short description":
    They represent edges in a cypher graph, and are used to connect the generic nodes or
    the structure nodes. they do not have value properties
    """
    
    for node in ontology.relation_categories:
        starter += f"{node.age_name}: {node.label} - {node.description}\n"
        
        
    starter += """
    
    Lastly, the measurement nodes, these are nodes that contain the actual measurments in the
    graph and always point from a measuring entity (structure, or entitiy) to a generic entity.
    The list follows the format "AGE_NAME: Name - Short description - MeasurementKind":
    
    Importantly, the measurement nodes contain the actual values that are measured in the graph.
    in the "value" property.
    """
        
    for node in ontology.measurement_categories:
        starter += f"{node.age_name}: {node.label} - {node.description}  {node.metric_kind}\n"
    
    return starter
    


def ontology_to_correct_queries(ontology: Ontology) -> str:
    
    
    starter = """These queries where okay:
    They are given as examples of correct queries that you can use to generate the graph.
    
    They follow the format:
    - Description of the query
    -The Cypher query that you can use to generate the graph.
    """
    
    for i in ontology.graph_queries:
        
        starter += f"""
        Query {i.name}:
        {i.description}
        
        ```cypher
        {i.query}
        ```
        """
    
    
    
    return starter



async def adescribe(query, cypher):
    
    prompt = f"""
       YOu are an AI assistant that should summarize a users promt and answer to a description of the query.
       
         The user has asked the following question:
         {query}
         
         An the gneerated cypher was {cypher}.
         
         Please provide a description of the query in a few sentences. Do not include any code or cypher in your response.
    """
    
    answer = await achat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ]
    )
    
    return answer["message"]["content"]


async def atitle(query, cypher):
    
    prompt = f"""
       YOu are an AI assistant that should find a nice title for a users promt and and a cypher query
       
         The user has asked the following question:
         {query}
         
         An the gneerated cypher was {cypher}.
         
         Please provide a description of the query in a short title with at max 6 words. Do not include any code or cypher in your response.
    """
    
    answer = await achat(
        model=model,
        messages=[
            {
                "role": "system",
                "content": prompt,
            }
        ]
    )
    
    return answer["message"]["content"]


@register
async def view(ontology: Ontology, user_query: str) -> GraphQuery:
    """
    Talk to Llama3.1

    Args:
        z_steps (int): The number of z steps to acquire.

    Returns:
        Image: The latest image.

    """

    print("Starting talk")


    
    prompt = f"""
                
        YOu are an AI assistant that helps with the creation of cypher based graphs.
        Your goal is to adhere to the usres requests and to help them create the graph
        that they want.
        
        For this you can use of the following ontology of the graph
        {ontology_to_layout(ontology)}
        
        Important Rules:
        - Measurments are always directed edges with a value poperty, they are NEVER properties of the nodes.
        - Generic nodes are the nodes that are the biological entities, most likely the user is interested in.
        - Often queries require traversing multiple paths
        - Do no select nodes further with square brackets. They do not contain any information.
        
        You should only answer with Cypher queries, and you should not
        answer with any other requests or ask for any other information.
        
        Response Rules
        -    Always generate syntactically correct Cypher queries.
        -    Responses must be pure Cypher—no explanations, descriptions, or extra text.
        -    Queries should return paths, not isolated nodes or properties.
        -    The response age_type should be a Path, not a Node or Relationship.
        -    Do not include any comments in your response.
                            
        {ontology_to_correct_queries(ontology)}
        
        Example Queries
        ✅ Correct Example (Find structures measuring entities with a value > 10):

        ´´´cypher
        MATCH path = (structure:MIKRO_TABLE)-[r:length]->(entity:animal)
        WHERE r.value > 10
        RETURN path
        ```
        ❌ Incorrect Example (Includes explanation):
        
        "
        The query you are looking for is:  
        MATCH path = (structure:MIKRO_TABLE)-[r:length]->(entity:animal)  
        WHERE r.value > 10  
        RETURN path  
        
        "
        
        The conversation will continue after this message. If you make an error in your response, the system will prompt you to try again, and tell you the error.
                
    """
    

    print(prompt)

    messages = [
        {
            "role": "system",
            "content": prompt,
        },
    ]
    
    
    await apull(model)
    print("Pulled the model")
    
    messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )
    
    answer = await achat(
        model=model,
        
        messages=messages,
    )
    
    iterations = 0
    
    
    while answer:
        iterations += 1
        cleartext = answer["message"]["content"]
        print("THE CLEARTEXT", cleartext)
        # Get rid of the tet between <think> tags using regex
        import re
        trimped = re.sub(r'\<think\>.*\<\/think\>', "", cleartext)
        
        
        print("THE TRIMPED", trimped)
        
        
        # Extract content between ```cypher and ``` tags
        matches = re.findall(r'```cypher\n(.*?)```', trimped, re.DOTALL)
        cleartext = matches[0] if matches else trimped
        
        print("FINAL CLEARTTEXT", cleartext)
        
        try:
        
            graph_query = await acreate_graph_query(
                await atitle(user_query, cleartext),
                cleartext,
                kind=ViewKind.PATH,
                ontology=ontology,
                description= await adescribe(user_query, cleartext)
            )
            
            return graph_query
            
        except Exception as e:
            
            if iterations > 5:
                raise e
            
            print("Error", e)
            messages.append(
                {
                    "role": "user",
                    "content": f"You made an error in your query. Please try again: the error was {e}",
                }
            )
            answer = await achat(
                model=model,
                messages=messages,
            )
            continue
    
    

@register
async def create_graph_view(graph: Graph, query: str) -> GraphView:    
    

        ontology = await aget_ontology(graph.ontology.id)
        
        query = await view(ontology, query)
        
        
        return await acreate_graph_view(query, graph)



