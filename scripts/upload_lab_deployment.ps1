$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$key = "$env:USERPROFILE\.ssh\ghl_codex_ed25519"
$archive = "$root\tmp\ghl-lab-deployment.tar.gz"

if (-not (Test-Path $key)) { throw "Missing SSH key: $key" }

Push-Location $root
try {
    tar.exe -czf $archive `
        --exclude=__pycache__ --exclude=node_modules --exclude=dist --exclude=.vinext --exclude=.wrangler `
        backend/app backend/pyproject.toml backend/scripts inference `
        web/app web/public web/worker web/build web/.openai `
        web/package.json web/package-lock.json web/vite.config.ts web/next.config.ts `
        web/postcss.config.mjs web/tsconfig.json web/eslint.config.mjs `
        deploy .dockerignore
    if ($LASTEXITCODE -ne 0) { throw "tar failed" }

    ssh -i $key -o BatchMode=yes -o IdentitiesOnly=yes ghl `
        "install -d -m 0750 /data/ghl/app /data/ghl/runtime /data/ghl/models/detector /data/ghl/models/experts"
    if ($LASTEXITCODE -ne 0) { throw "remote directory preparation failed" }
    scp -i $key -o BatchMode=yes -o IdentitiesOnly=yes $archive "ghl:/data/ghl/runtime/ghl-lab-deployment.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw "deployment archive upload failed" }
    ssh -i $key -o BatchMode=yes -o IdentitiesOnly=yes ghl `
        "tar -xzf /data/ghl/runtime/ghl-lab-deployment.tar.gz -C /data/ghl/app && bash /data/ghl/app/deploy/lab/bootstrap-layout.sh"
    if ($LASTEXITCODE -ne 0) { throw "deployment extraction failed" }

    scp -i $key -o BatchMode=yes -o IdentitiesOnly=yes `
        "$root\artifacts\server\remote-runs\official-plus-public-weak-v1-e120-b64\weights\best.pt" `
        "ghl:/data/ghl/models/detector/main.pt"
    scp -i $key -o BatchMode=yes -o IdentitiesOnly=yes `
        "$root\artifacts\server\experiments\weak-expert-v2-full-public10-ft-freeze10-lr1e4-e18-b64\best.pt" `
        "ghl:/data/ghl/models/experts/class10.pt"
    scp -i $key -o BatchMode=yes -o IdentitiesOnly=yes `
        "$root\artifacts\server\experiments\pairwise-crop-cls-10-13-v5-e30-b128\best.pt" `
        "ghl:/data/ghl/models/experts/crop-classifier.pt"
    if ($LASTEXITCODE -ne 0) { throw "model upload failed" }

    ssh -i $key -o BatchMode=yes -o IdentitiesOnly=yes ghl `
        "sha256sum /data/ghl/models/detector/main.pt /data/ghl/models/experts/class10.pt /data/ghl/models/experts/crop-classifier.pt"
    if ($LASTEXITCODE -ne 0) { throw "remote model verification failed" }
}
finally {
    Pop-Location
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
}
