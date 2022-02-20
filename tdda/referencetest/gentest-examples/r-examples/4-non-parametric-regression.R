# Fit non-parametric curves to observations

source("0-set-variables.R")

# Plot resulting curve fits with binned data

library(gam)             # Load GAM library
modlist.gam <- as.list(rep(NA, times = length(taxa.names)))
for (i in 1:length(taxa.names)) {

                  # Create a logical vector that is true if taxon is
                  # present and false if taxon is absent.
     resp <- dfmerge[, taxa.names[i]]>0

                  # Fit the regression model, specifying two degrees of freedom
                  # to the curve fit.
     modlist.gam[[i]] <- gam(resp ~ s(temp, df = 2), data = dfmerge,
                   family = "binomial")

     print(summary(modlist.gam[[i]]))
}

postscript('plots4.ps')
par(mfrow = c(1,3), pty = "s")
for (i in 1:length(taxa.names)) {

predres <- predict(modlist.gam[[i]], type= "link", se.fit = T)

     up.bound.link <- predres$fit + 1.65*predres$se.fit
     low.bound.link <- predres$fit - 1.65*predres$se.fit
     mean.resp.link <- predres$fit

     up.bound <- exp(up.bound.link)/(1+exp(up.bound.link))
     low.bound <- exp(low.bound.link)/(1+exp(low.bound.link))
     mean.resp <- exp(mean.resp.link)/(1+exp(mean.resp.link))

     iord <- order(dfmerge$temp)

     nbin <- 20
     cutp <- quantile(dfmerge$temp, probs = seq(from = 0, to = 1, length = 20))

     cutm <- 0.5*(cutp[-1] + cutp[-nbin])
     cutf <- cut(dfmerge$temp, cutp, include.lowest = T)
     vals <- tapply(dfmerge[, taxa.names[i]] > 0, cutf, mean)

     plot(cutm, vals, xlab = "Temperature",
     ylab = "Probability of occurrence", ylim = c(0,1),
     main = taxa.names[i])

     lines(dfmerge$temp[iord], mean.resp[iord])
     lines(dfmerge$temp[iord], up.bound[iord], lty = 2)
     lines(dfmerge$temp[iord], low.bound[iord], lty = 2)
}
dev.off()

