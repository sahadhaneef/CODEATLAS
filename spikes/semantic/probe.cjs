// Server-owned probe: an in-memory source host, no project/config/package discovery or emit.
const ts = require('typescript');
const source = '// 😀\r\nfunction greet(name: string): string { return name; }\r\nconst answer = greet("ok");\r\n';
const path = '/fixture.ts';
const options = { noLib: true, noEmit: true, noResolve: true, target: ts.ScriptTarget.ES2022 };
const host = {
  getSourceFile: (name, version) => name === path ? ts.createSourceFile(name, source, version, true) : undefined,
  getDefaultLibFileName: () => '', writeFile: () => { throw Error('emit prohibited'); },
  getCurrentDirectory: () => '/', getDirectories: () => [], getCanonicalFileName: x => x,
  useCaseSensitiveFileNames: () => true, getNewLine: () => '\n',
  fileExists: name => name === path, readFile: name => name === path ? source : undefined,
};
const program = ts.createProgram([path], options, host);
const checker = program.getTypeChecker();
let result;
function visit(node) {
  if (ts.isCallExpression(node)) {
    const declaration = checker.getResolvedSignature(node)?.declaration;
    const start = declaration?.getStart();
    result = {
      call: node.expression.getText(), declaration: declaration?.name?.getText(),
      returnType: checker.typeToString(checker.getTypeAtLocation(node)),
      startUtf16: start, startByte: Buffer.byteLength(source.slice(0, start), 'utf8'),
      line: declaration && declaration.getSourceFile().getLineAndCharacterOfPosition(start).line + 1,
      resolution: declaration ? 'resolved' : 'unknown',
    };
  }
  ts.forEachChild(node, visit);
}
visit(program.getSourceFile(path));
if (!result || result.declaration !== 'greet' || result.returnType !== 'string' || result.line !== 2)
  throw Error('controlled signature resolution failed');
process.stdout.write(JSON.stringify({ version: ts.version, ...result, configLoaded: false, emitted: false }));
