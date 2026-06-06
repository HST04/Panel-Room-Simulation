# Lab 1 - Overview of embeddings-based retrieval

Welcome! Here's a few notes about the Chroma course notebooks.
 - A number of warnings pop up when running the notebooks. These are normal and can be ignored.
 - Some operations such as calling an LLM or an opeation using generated data return unpredictable results and so your notebook outputs may differ from the video.
  
Enjoy the course!


```python
from helper_utils import word_wrap
```


```python
from pypdf import PdfReader

reader = PdfReader("microsoft_annual_report_2022.pdf")
pdf_texts = [p.extract_text().strip() for p in reader.pages]

# Filter the empty strings
pdf_texts = [text for text in pdf_texts if text]

print(word_wrap(pdf_texts[0]))
```

    1 Dear shareholders, colleagues, customers, and partners:  
    We are
    living through a period of historic economic, societal, and
    geopolitical change. The world in 2022 looks nothing like 
    the world in
    2019. As I write this, inflation is at a 40 -year high, supply chains
    are stretched, and the war in Ukraine is 
    ongoing. At the same time, we
    are entering a technological era with the potential to power awesome
    advancements 
    across every sector of our economy and society. As the
    world’s largest software company, this places us at a historic
    
    intersection of opportunity and responsibility to the world around us.
     
    Our mission to empower every person and every organization on the
    planet to achieve more has never been more 
    urgent or more necessary.
    For all the uncertainty in the world, one thing is clear: People and
    organizations in every 
    industry are increasingly looking to digital
    technology to overcome today’s challenges and emerge stronger. And no
    
    company is better positioned to help them than Microsoft.  
    Every day
    this past fiscal year I have had the privilege to witness our customers
    use our platforms and tools to connect 
    what technology can do with
    what the world needs  it to do.  
    Here are just a few examples:  
    •
    Ferrovial, which builds and manages some of the world’s busiest
    airports and highways, is using our cloud 
    infrastructure to build
    safer roads as it prepares for a future of autonomous transportation. 
    
    • Peace Parks Foundation, a nonprofit helping protect natural
    ecosystems in Southern Africa, is using Microsoft 
    Dynamics 365 and
    Power BI to secure essential funding, as well as our Azure AI and IoT
    solutions to help 
    rangers scale their park maintenance and wildlife
    crime prevention work.  
    • One of the world’s largest robotics
    companies, Kawasaki Heavy Industries, is using the breadth of our tools
    —
    from Azure IoT and HoloLens —to create an industrial metaverse
    solution that brings its distributed workforce 
    together with its
    network of connected equipment to improve productivity and keep
    employees safe.  
    • Globo, the biggest media and TV company in Brazil,
    is using Power Platform to empower its employees to 
    build their own
    solutions for everything from booking sets to setting schedules.  
    •
    And Ørsted, which produces a quarter of the world’s wind energy, is
    using the Microsoft Intelligent Data 
    Platform to turn data from its
    offshore turbines into insights for predictive maintenance.  
    Amid this
    dynamic environment, we delivered record results in fiscal year 2022:
    We reported $198  billion in revenue and 
    $83 billion in operating
    income. And the Microsoft Cloud surpassed $100  billion in annualized
    revenue for the first time.  
    OUR RESPONSIBILITY  
    As a corporation,
    our purpose and actions must be aligned with addressing the world’s
    problems, not creating new ones. 
    At our very core, we need to deliver
    innovation that helps drive broad economic growth. We, as a company,
    will do well 
    when the world around us does well.  
    That’s what I
    believe will lead to widespread human progress and ultimately improve
    the lives of everyone. There is no 
    more powerful input than digital
    technology to drive the world’s economic output. This is the core
    thesis for our being as a 
    company, but it’s not enough. As we drive
    global economic growth, we must also commit to creating a more
    inclusive, 
    equitable, sustainable, and trusted future.  
    Support
    inclusive economic growth  
    We must ensure the growth we drive reaches
    every person, organization, community, and country. This starts with
    
    increasing access to digital skills. This year alone, more than 23 
    million people accessed digital skills training as part of 
    our global
    skills initiative.


You can view the pdf in your browser [here](./microsoft_annual_report_2022.pdf) if you would like. 


```python
from langchain.text_splitter import RecursiveCharacterTextSplitter, SentenceTransformersTokenTextSplitter

```


```python
character_splitter = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ". ", " ", ""],
    chunk_size=1000,
    chunk_overlap=0
)
character_split_texts = character_splitter.split_text('\n\n'.join(pdf_texts))

print(word_wrap(character_split_texts[10]))
print(f"\nTotal chunks: {len(character_split_texts)}")
```

    increased, due in large part to significant global datacenter
    expansions and the growth in Xbox sales and usage. Despite 
    these
    increases, we remain dedicated to achieving a net -zero future. We
    recognize that progress won’t always be linear, 
    and the rate at which
    we can implement emissions reductions is dependent on many factors that
    can fluctuate over time.  
    On the path to becoming water positive, we
    invested in 21 water replenishment projects that are expected to
    generate 
    over 1.3  million cubic meters of volumetric benefits in nine
    water basins around the world. Progress toward our zero waste
    
    commitment included diverting more than 15,200 metric tons of solid
    waste otherwise headed to landfills and incinerators, 
    as well as
    launching new Circular Centers to increase reuse and reduce e -waste at
    our datacenters.  
    We contracted to protect over 17,000 acres of land
    (50% more than the land we use to operate), thus achieving our
    
    Total chunks: 347



```python
token_splitter = SentenceTransformersTokenTextSplitter(chunk_overlap=0, tokens_per_chunk=256)

token_split_texts = []
for text in character_split_texts:
    token_split_texts += token_splitter.split_text(text)

print(word_wrap(token_split_texts[10]))
print(f"\nTotal chunks: {len(token_split_texts)}")
```


```python
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

embedding_function = SentenceTransformerEmbeddingFunction()
print(embedding_function([token_split_texts[10]]))
```


```python
chroma_client = chromadb.Client()
chroma_collection = chroma_client.create_collection("microsoft_annual_report_2022", embedding_function=embedding_function)

ids = [str(i) for i in range(len(token_split_texts))]

chroma_collection.add(ids=ids, documents=token_split_texts)
chroma_collection.count()
```


```python
query = "What was the total revenue?"

results = chroma_collection.query(query_texts=[query], n_results=5)
retrieved_documents = results['documents'][0]

for document in retrieved_documents:
    print(word_wrap(document))
    print('\n')
```


```python
import os
import openai
from openai import OpenAI

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
openai.api_key = os.environ['OPENAI_API_KEY']

openai_client = OpenAI()
```


```python
def rag(query, retrieved_documents, model="gpt-3.5-turbo"):
    information = "\n\n".join(retrieved_documents)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful expert financial research assistant. Your users are asking questions about information contained in an annual report."
            "You will be shown the user's question, and the relevant information from the annual report. Answer the user's question using only this information."
        },
        {"role": "user", "content": f"Question: {query}. \n Information: {information}"}
    ]
    
    response = openai_client.chat.completions.create(
        model=model,
        messages=messages,
    )
    content = response.choices[0].message.content
    return content
```


```python
output = rag(query=query, retrieved_documents=retrieved_documents)

print(word_wrap(output))
```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```


```python

```
