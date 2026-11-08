# Dockerfile for Krona Visualization
################## BASE IMAGE ######################
FROM biocontainers/biocontainers:v1.2.0_cv2

################## METADATA ######################
LABEL base_image="biocontainers:v1.2.0_cv2"
LABEL version="1"
LABEL software="krona"
LABEL software.version="2.8.1"
LABEL about.summary="Krona Tools is a set of scripts to create Krona charts from several Bioinformatics tools as well as from text and XML files."
LABEL about.home="https://github.com/marbl/Krona"
LABEL about.documentation="https://github.com/marbl/Krona/wiki"
LABEL about.license_file="https://github.com/marbl/Krona/blob/master/KronaTools/LICENSE.txt"
LABEL about.license="BSD"
LABEL about.tags="General"

ARG http_proxy
ARG https_proxy

################## INSTALLATION ######################
USER root

RUN apt-get clean && \
    apt-get update && \
    apt-get install -y apt-utils curl && \
    conda install -c bioconda krona=2.8.1 && \
    ktUpdateTaxonomy.sh && \
    apt-get clean && \
    apt-get purge && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# USER biodocker

# WORKDIR /data/

# Set the entrypoint
# ENTRYPOINT ["ktImportTaxonomy"]