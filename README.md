# Consultation Biodiversité

## Install:

- Node.js dependencies:

```bash
cd moissonneur-API
npm install
```

- Python dependencies (in your choice of sudo or virtualenv):

```bash
pip install requests networkx
```

## Collect and build data:

### Collect parlement-et-citoyens API data:

```bash
cd moissonneur-API
node fetch-json.js ../data-contributions
```

### Scrap parlement-et-citoyens users data for this project:

Takes a few hours

```bash
./scrap.py projet-de-loi-pour-la-reconquete-de-la-biodiversite-de-la-nature-et-des-paysages
```

### Build GEXF networks:

```bash
./build_networks.py
# Build lighter networks by filtering low linkage
for i in `seq 1 9`; do
  grep -v 'weight="[0-'$i']"' data/contributions.gexf > data/contributions-w$(($i+1))+.gexf
done
```

