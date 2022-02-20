# Set up R files for running scripts

# working directory.

# Load data into R
site.species <- read.delim("site.species.txt")
site.species.or <- read.delim("site.species.or.txt")
env.data <- read.delim("env.data.txt")
env.data.or <- read.delim("env.data.or.txt")
# refids <- read.delim("refids.or.txt")

# Merge biological and environmental data
dfmerge <- merge(site.species, env.data, by = "SITE.ID")
dfmerge.or <- merge(site.species.or, env.data.or, by = "SITE.ID")

# Set taxa.names
taxa.names <- c("ACENTRELLA", "DIPHETOR", "AMELETUS")
