# Fit parametric regression models to observations
# Plot resulting curve fits with binned data

source("0-set-variables.R")

# Create storage list
modlist.glm <- as.list(rep(NA, times = length(taxa.names)))

for (i in 1:length(taxa.names)) {

    # Create a logical vector that is true if taxon is
    # present and false if taxon is absent.

    resp <- dfmerge[,taxa.names[i]]>0

    # Fit the regression model and store the results in a list.
    # Here, poly(temp,2) specifies that the
    # model is fitting using a second order polynomial of the
    # explanatory variable. glm calls the function that fits
    # Generalized Linear Models. We specify in this case that
    # the response variable is distributed binomially.
    modlist.glm[[i]] <- glm(resp ~ poly(temp,2), data = dfmerge,
    family = "binomial")

    print(summary(modlist.glm[[i]]))
}

postscript('plots3.ps')
par(mfrow = c(1,3), pty = "s")
    # Specify 3 plots per page
for (i in 1:length(taxa.names)) {
    # Compute mean predicted probability of occurrence
    # and standard errors about this predicted probability.
    predres <- predict(modlist.glm[[i]], type= "link", se.fit = T)

    # Compute upper and lower 90% confidence limits
    up.bound.link <- predres$fit + 1.65*predres$se.fit
    low.bound.link <- predres$fit - 1.65*predres$se.fit
    mean.resp.link <- predres$fit

    # Convert from logit transformed values to probability.
    up.bound <- exp(up.bound.link)/(1+exp(up.bound.link))
    low.bound <- exp(low.bound.link)/(1+exp(low.bound.link))
    mean.resp <- exp(mean.resp.link)/(1+exp(mean.resp.link))

    iord <- order(dfmerge$temp)
    # Sort the environmental variable.

    # Define bins to summarize observational data as
    # probabilities of occurrence

    # Define the number of bins
    nbin <- 20

    # Define bin boundaries so each bin has approximately the same
    # number of observations.
    cutp <- quantile(dfmerge$temp,probs = seq(from = 0, to = 1, length = 20))

    # Compute the midpoint of each bin
    cutm <- 0.5*(cutp[-1] + cutp[-nbin])

    # Assign a factor to each bin
    cutf <- cut(dfmerge$temp, cutp, include.lowest = T)

    # Compute the mean of the presence/absence data within each
    # bin.
    vals <- tapply(dfmerge[, taxa.names[i]] > 0, cutf, mean)

    # Now generate the plot, # Plot binned observational data as symbols.
    plot(cutm, vals, xlab = "Temperature",
    ylab = "Probability of occurrence", ylim = c(0,1),
    main = taxa.names[i])

    # Plot mean fit as a solid line.
    lines(dfmerge$temp[iord], mean.resp[iord])

    # Plot confidence limits as dotted lines.
    lines(dfmerge$temp[iord], up.bound[iord], lty = 2)
    lines(dfmerge$temp[iord], low.bound[iord], lty = 2)
}
dev.off()
