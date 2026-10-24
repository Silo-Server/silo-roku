// BrighterScript plugin: fail the build on any warning, including bslint's.
// Registered after bslint's own rule plugins so their diagnostics are promoted too.
const { DiagnosticSeverity } = require('brighterscript');

module.exports = () => ({
    name: 'warnings-as-errors',
    afterProgramCreate(program) {
        // BrighterScript reapplies severity overrides after this plugin runs, so an
        // override to anything but error would quietly let that warning through.
        const overrides = program.options.diagnosticSeverityOverrides ?? {};
        for (const [code, severity] of Object.entries(overrides)) {
            if (severity === 'error') continue;
            console.error(`warnings-as-errors: diagnosticSeverityOverrides ${code}: "${severity}" is treated as "error"`);
            overrides[code] = 'error';
        }
        program.plugins.add({
            name: 'warnings-as-errors-promote',
            afterProgramValidate() {
                for (const diagnostic of program.getDiagnostics()) {
                    if (diagnostic.severity === DiagnosticSeverity.Warning) diagnostic.severity = DiagnosticSeverity.Error;
                }
            }
        });
    }
});
