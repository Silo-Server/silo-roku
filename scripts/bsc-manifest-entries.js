// BrighterScript plugin: write build-variant values into the staged manifest.
// bsconfig "manifestEntries" sets keys bsc cannot override (run_as_process), and
// bs_const is rewritten to bsc's merged value so the package matches the
// "manifest.bs_const" overrides the code was compiled with.
const fs = require('fs');
const path = require('path');

module.exports = () => ({
    name: 'manifest-entries',
    afterPublish(builder) {
        const values = { ...builder.options.manifestEntries };
        const bsConst = builder.program.getManifest().get('bs_const');
        if (bsConst) values.bs_const = bsConst;
        const file = path.resolve(builder.options.cwd, builder.options.stagingDir, 'manifest');
        const kept = fs.readFileSync(file, 'utf8').split(/\r?\n/)
            .filter((line) => line && !Object.hasOwn(values, line.split('=')[0].trim()));
        const added = Object.entries(values).map(([key, value]) => `${key}=${value}`);
        fs.writeFileSync(file, [...kept, ...added, ''].join('\n'));
    }
});
