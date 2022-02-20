# Script to compute cumulative percentiles

source("0-set-variables.R")

CP <- rep(NA, times = length(taxa.names))
# Define a storage vector for the cumulative percentile

dftemp <- dfmerge[order(dfmerge$temp), ]
                                                           # Sort sites by the value
                                                           # of the environmental
                                                           # variable

cutoff <- 0.75
                                                           # Select a cutoff percentile

pdf('plots2.pdf')
par(mfrow = c(1,3), pty = "s")
                                                           # Specify three plots per page
for (i in 1:length(taxa.names)) {
     csum <- cumsum(dftemp[, taxa.names[i]])/
     sum(dftemp[,taxa.names[i]])
                                                           # Compute cumulative sum
                                                           # of abundances
     plot(dftemp$temp, csum, type = "l", xlab = "Temperature",
          ylab = "Proportion of total", main = taxa.names[i])
                                                           # Make plots like Figure 5
     ic <- 1
     while (csum[ic] < 0.75) ic <- ic + 1
                                                           # Search for point at which
                                                           # cumulative sum is 0.75
     CP[i] <- dftemp$temp[ic]
                                                           # Save the temperature that
                                                           # corresponds to this
                                                           # percentile.
     }
names(CP) <- taxa.names
print(CP)
dev.off()
