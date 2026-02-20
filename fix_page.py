import sys

path = '/Users/axelfernandes/Desktop/applications/axel/axel-web/src/app/dashboard/page.tsx'
with open(path, 'r') as f:
    lines = f.readlines()

new_header = [
    '          {selectedRepo && (\n',
    '            <>\n',
    '              <button\n',
    '                onClick={handleIndexRepo}\n',
    '                disabled={isIndexing}\n',
    '                title="Index codebase for RAG"\n',
    '                className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${isIndexing ? "bg-blue-900 text-blue-200" : "bg-gray-800 text-gray-300 hover:bg-gray-700 hover:text-white"}`}\n',
    '              >\n',
    '                {isIndexing ? (\n',
    '                  <Loader2 className="h-3.5 w-3.5 animate-spin" />\n',
    '                ) : (\n',
    '                  <Database className="h-3.5 w-3.5" />\n',
    '                )}\n',
    '                <span>{isIndexing ? "Indexing..." : "Index"}</span>\n',
    '              </button>\n',
    '\n',
    '              {projectMode !== "web" && (\n',
    '                <button\n',
    '                  onClick={handleScaffold}\n',
    '                  disabled={isScaffolding}\n',
    '                  title={`Scaffold ${projectMode} project`}\n',
    '                  className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors ${isScaffolding ? "bg-purple-900 text-purple-200" : "bg-purple-600 text-white hover:bg-purple-700"}`}\n',
    '                >\n',
    '                  {isScaffolding ? (\n',
    '                    <Loader2 className="h-3.5 w-3.5 animate-spin" />\n',
    '                  ) : (\n',
    '                    <Sparkles className="h-3.5 w-3.5" />\n',
    '                  )}\n',
    '                  <span>{isScaffolding ? "Scaffolding..." : "Scaffold"}</span>\n',
    '                </button>\n',
    '              )}\n',
    '            </>\n',
    '          )}\n'
]

# We want to replace exactly what we saw in the view_file between lines 342 and 376.
# 1-indexed 342:376 becomes 0-indexed 341:375.
# Let's double check if lines[341] is indeed '{selectedRepo && ('
if len(lines) > 341 and '{selectedRepo && (' in lines[341]:
    lines[341:375] = new_header
    with open(path, 'w') as f:
        f.writelines(lines)
    print("Success: Header fixed.")
else:
    print(f"Error: Could not find target line at index 341. Found: {lines[341] if len(lines) > 341 else 'EOF'}")
