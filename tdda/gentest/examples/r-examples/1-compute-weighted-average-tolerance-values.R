# Script to compute WA tolerance values

source("0-set-variables.R")

WA <- rep(NA, times = length(taxa.names))
            # Define a WA to be vector of
            # length the same as the
            # number of taxa of interest

for (i in 1:length(taxa.names)) {
  WA[i] <- sum(dfmerge[,taxa.names[i]]*dfmerge$temp)/
   sum(dfmerge[,taxa.names[i]])
}
names(WA) <- taxa.names
print(WA)
