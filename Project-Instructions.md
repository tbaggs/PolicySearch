This is a multi-part application to process policy documents into a searchable index using Azure AI Search with several agents.  

# Part 1
The goal is to get a list of similar policy titles from a master record list of policy titles.

To accomplish this we will be building an Azure AI Search index by indexing each entry in the file PolicyDocTitles.csv.  The first field is the policy title and the second field is the URL for the location of the policy.

## Steps
1. Define an Azure AI Search index definition with field primary fields and then a vector field for PolicyTitle. 

- PolicyTitle
- PolicyTitleVector
- PolicyURL
- PrimaryPolicy
- SecondaryPolicy

Policy Title will need to have an embedded vector in order to make it searchable.

2. Create an indexer that read each entry in the PolicyDocTitles.csv and index the content

## Notes

- Generate all code in Python and create json definitions for all Azure AI Search components.

