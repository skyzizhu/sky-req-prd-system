// Each suite receives its own temporary project; never mutate a user's delivered case.
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const repo=path.resolve(__dirname,'..');
const work=fs.mkdtempSync(path.join(os.tmpdir(),'prd-browser-'));
const suites=[
  ['static-reader','scripts/create_static_demo.py'],
  ['local-controls',null],
  ['list-annotations',null],
  ['production-reader','scripts/create_static_demo.py'],
  ['artboard-surfaces',null],
  ['consumer-mobile',null],
  ['maintenance',null],
  ['reader-usability',null],
  ['rule-reading',null],
  ['special-cases',null],
  ['diagrams','scripts/create_static_demo.py'],
  ['editor','tests/fixtures/versioned_project.py'],
  ['prd','tests/fixtures/versioned_project.py'],
  ['delivery','tests/fixtures/versioned_project.py'],
  ['handoff','tests/fixtures/versioned_project.py'],
  ['outcomes',null],
  ['standard-prd','tests/fixtures/versioned_project.py']
];
let failed=false;
for(const [name,generator] of suites){
  const root=path.join(work,name),shots=path.join(work,name+'-shots');
  fs.mkdirSync(shots);
  try{
    if(generator)execFileSync('python3',[generator,root],{cwd:repo,timeout:60000,stdio:'pipe'});
    const output=execFileSync(process.execPath,[path.join(__dirname,name+'-browser.cjs'),root,['prd','standard-prd','outcomes'].includes(name)?path.join(shots,name+'.png'):shots],{cwd:repo,timeout:60000,encoding:'utf8'});
    process.stdout.write(output);
  }catch(error){
    failed=true;console.error('FAIL '+name+': '+error.message);
  }
}
if(failed){console.error('Failed-suite artifacts: '+work);process.exitCode=1;}
else{fs.rmSync(work,{recursive:true,force:true});console.log('PASS all '+suites.length+' browser suites (isolated projects cleaned)');}
