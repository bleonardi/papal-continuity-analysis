# Deploy rag-chat.qmd to shinyapps.io.
#
# Run from the repo root: Rscript rag/deploy.R
#
# Why this isn't just `rsconnect::deployDoc("rag-chat.qmd")`: rag-chat.qmd
# lives at the repo root, so the naive deploy bundles every file under the
# repo -- data/raw/'s ~5,500 scraped text files included. And why this
# isn't `deployApp(appFiles = c(...))` either: passing appFiles explicitly
# disables rsconnect's automatic R-package dependency scan, so the deployed
# app has no packages installed and fails to start (`shiny package was not
# found in the library`).
#
# The fix that actually works: copy only the files the app needs into an
# isolated staging directory, render there (shinyapps.io does NOT
# pre-render Shiny Quarto content server-side -- it expects the rendered
# rag-chat.html + rag-chat_files/ already in the bundle, or it fails with
# "Prerendered HTML file not found"), then deploy *that* directory with no
# appFiles restriction. Because the staging directory only contains what's
# needed, the natural (unrestricted) scan produces both the right file list
# and the right dependencies.
#
# Getting GOOGLE_API_KEY to the deployed app: shinyapps.io (unlike Posit
# Connect) has neither a dashboard "Vars" page nor rsconnect::deployApp's
# envVars parameter -- deployApp() errors outright with "shinyapps.io does
# not support setting envVars" if you try. The only thing that actually
# works is bundling a .Renviron file with the deploy: R reads .Renviron
# from its working directory at startup as a base-R feature, independent
# of any platform support, and the app's working directory is exactly
# where the deploy bundle lands. This script writes one into the staging
# directory only -- it is never written into the git repo, so the key
# never touches version control.

library(rsconnect)

google_api_key <- Sys.getenv("GOOGLE_API_KEY")
if (!nzchar(google_api_key)) google_api_key <- Sys.getenv("GEMINI_API_KEY")
if (!nzchar(google_api_key)) {
  stop("Set GOOGLE_API_KEY (or GEMINI_API_KEY) in your local R session/",
       ".Renviron before running this script -- it gets bundled into the ",
       "deploy so the live app can authenticate to Gemini.")
}

# Assumes the working directory is the repo root (as instructed above).
repo_root <- normalizePath(".")
stopifnot(file.exists(file.path(repo_root, "rag-chat.qmd")))

stage <- file.path(tempdir(), "rag-chat-deploy")
unlink(stage, recursive = TRUE)
dir.create(file.path(stage, "rag"), recursive = TRUE)
dir.create(file.path(stage, "assets"), recursive = TRUE)

file.copy(file.path(repo_root, "rag-chat.qmd"), stage)
file.copy(file.path(repo_root, "rag", "corpus.json"), file.path(stage, "rag"))
file.copy(file.path(repo_root, "assets", "custom.scss"), file.path(stage, "assets"))
writeLines(
  sprintf("GOOGLE_API_KEY=%s", google_api_key),
  file.path(stage, ".Renviron")
)

old_wd <- setwd(stage)
system2("quarto", c("render", "rag-chat.qmd"))
setwd(old_wd)

rsconnect::deployApp(
  appDir = stage,
  appPrimaryDoc = "rag-chat.qmd",
  appId = 17595037,
  appName = "papal-rag-chat",
  account = "benedictleonardi",
  server = "shinyapps.io",
  forceUpdate = TRUE,
  launch.browser = FALSE
)

cat("Deployed from", stage, "\n")
