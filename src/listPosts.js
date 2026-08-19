// Atualiza a seção 'Últimos posts do blog' do README.md a partir do posts-feed.json
// do site (https://frederico-kluser.com/posts-feed.json — um único arquivo JSON com
// links e títulos em inglês, gerado no build do site). Executado pelo workflow
// .github/workflows/blog-posts.yml, que baixa o arquivo antes.
const { readFileSync, writeFileSync } = require('fs');

const feed = JSON.parse(readFileSync('posts-feed.json', 'utf8'));

if (!Array.isArray(feed)) {
  throw new Error('posts-feed.json não é um array — seção NÃO foi alterada');
}

const posts = feed.slice(0, 5).map((item) => {
  const date = typeof item.date === 'string' ? item.date : '';
  return '-   ' + date + ' [' + item.title + '](' + item.url + '?utm_source=GitHubProfile)';
});

if (posts.length === 0) {
  throw new Error('Nenhum post em posts-feed.json — seção NÃO foi alterada');
}

const START = '<!--START_SECTION:blog-posts-->';
const END = '<!--END_SECTION:blog-posts-->';

const readme = readFileSync('README.md', 'utf8');
const startIdx = readme.indexOf(START);
const endIdx = readme.indexOf(END);

if (startIdx === -1 || endIdx === -1 || endIdx < startIdx) {
  throw new Error('Marcadores ' + START + ' / ' + END + ' não encontrados no README.md');
}

const updated =
  readme.slice(0, startIdx + START.length) +
  '\n' + posts.join('\n') + '\n' +
  readme.slice(endIdx);

writeFileSync('README.md', updated);
console.log('[blog-posts] ' + posts.length + ' posts escritos no README.md');