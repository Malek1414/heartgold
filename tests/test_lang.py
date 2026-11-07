# Copyright 2026 Malek Hassan (https://github.com/Malek1414/heartgold)
# SPDX-License-Identifier: Apache-2.0
"""Every language adapter, on a real tiny project: the repo's own tests run on their own and pass, heartgold's
spec test runs on its own and its failure is counted, and the probe prints the protocol's JSON array.

Each project implements add(a, b). Its own test passes; heartgold's spec test expects add(2, 2) == 5, so it must
fail; the probe calls add(2, 2) and add(0, 0) and must print ["=4", "=0"]. A language whose toolchain is missing
is skipped, and says so."""
import json, os, pathlib, shutil, subprocess

import pytest

from heartgold.lang import LANGS, detect, parse_results

ENV = {**os.environ, "PATH": f"{pathlib.Path.home()}/.local/bin:{subprocess.run(['ruby', '-e', 'print Gem.user_dir'], capture_output=True, text=True).stdout if shutil.which('ruby') else ''}/bin:{os.environ['PATH']}"}

F = {
    "python": {
        "pyproject.toml": "[project]\nname = 'fx'\nversion = '0'\n",
        "fx.py": "def add(a, b):\n    return a + b\n",
        "tests/test_fx.py": "from fx import add\n\ndef test_add():\n    assert add(1, 2) == 3\n",
        "tests/test_heartgold_spec.py": "from fx import add\n\ndef test_heartgold_spec_add():\n    assert add(2, 2) == 5\n",
    },
    "js": {
        "package.json": '{"name": "fx", "type": "module"}\n',
        "fx.mjs": "export const add = (a, b) => a + b;\n",
        "tests/fx.test.mjs": "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { add } from '../fx.mjs';\ntest('add', () => assert.equal(add(1, 2), 3));\n",
        "tests/heartgold_spec.test.mjs": "import { test } from 'node:test';\nimport assert from 'node:assert';\nimport { add } from '../fx.mjs';\ntest('heartgold spec add', () => assert.equal(add(2, 2), 5));\n",
        ".heartgold_probe.mjs": "import { add } from './fx.mjs';\nconst out = [[2, 2], [0, 0]].map(([a, b]) => { try { return '=' + JSON.stringify(add(a, b)); } catch (e) { return '!' + e.name; } });\nconsole.log(JSON.stringify(out));\n",
    },
    "rust": {
        "Cargo.toml": '[package]\nname = "fx"\nversion = "0.1.0"\nedition = "2021"\n',
        "src/lib.rs": "pub fn add(a: i64, b: i64) -> i64 { a + b }\n",
        "tests/basic.rs": "#[test]\nfn add_works() { assert_eq!(fx::add(1, 2), 3); }\n",
        "tests/heartgold_spec.rs": "#[test]\nfn heartgold_spec_add() { assert_eq!(fx::add(2, 2), 5); }\n",
        "examples/heartgold_probe.rs": 'fn main() { let out: Vec<String> = [(2, 2), (0, 0)].iter().map(|&(a, b)| format!("\\"={}\\"", fx::add(a, b))).collect(); println!("[{}]", out.join(",")); }\n',
    },
    "go": {
        "go.mod": "module fx\n\ngo 1.21\n",
        "fx.go": "package fx\n\nfunc Add(a, b int) int { return a + b }\n",
        "fx_test.go": "package fx\n\nimport \"testing\"\n\nfunc TestAdd(t *testing.T) { if Add(1, 2) != 3 { t.Fatal(\"bad\") } }\n",
        "heartgold_spec_test.go": "package fx\n\nimport \"testing\"\n\nfunc TestHeartgoldSpecAdd(t *testing.T) { if Add(2, 2) != 5 { t.Fatal(\"spec\") } }\n",
        "cmd/heartgold_probe/main.go": 'package main\n\nimport (\n\t"encoding/json"\n\t"fmt"\n\t"fx"\n)\n\nfunc main() {\n\tout := []string{}\n\tfor _, c := range [][2]int{{2, 2}, {0, 0}} {\n\t\tb, _ := json.Marshal(fx.Add(c[0], c[1]))\n\t\tout = append(out, "="+string(b))\n\t}\n\tj, _ := json.Marshal(out)\n\tfmt.Println(string(j))\n}\n',
    },
    "java": {
        "pom.xml": """<project xmlns="http://maven.apache.org/POM/4.0.0"><modelVersion>4.0.0</modelVersion>
<groupId>fx</groupId><artifactId>fx</artifactId><version>0</version>
<properties><maven.compiler.release>17</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
<dependencies><dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>5.11.3</version><scope>test</scope></dependency></dependencies>
<build><plugins><plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.5.2</version></plugin></plugins></build>
</project>
""",
        "src/main/java/Fx.java": "public class Fx { public static int add(int a, int b) { return a + b; } }\n",
        "src/test/java/FxTest.java": "import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\nclass FxTest { @Test void add() { assertEquals(3, Fx.add(1, 2)); } }\n",
        "src/test/java/HeartgoldSpecTest.java": "import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;\nclass HeartgoldSpecTest { @Test void add() { assertEquals(5, Fx.add(2, 2)); } }\n",
        "src/main/java/HeartgoldProbe.java": 'public class HeartgoldProbe { public static void main(String[] a) { System.out.println("[\\"=" + Fx.add(2, 2) + "\\",\\"=" + Fx.add(0, 0) + "\\"]"); } }\n',
    },
    "ruby": {
        "Gemfile": "source 'https://rubygems.org'\n",
        "lib/fx.rb": "module Fx\n  def self.add(a, b) = a + b\nend\n",
        "spec/fx_spec.rb": "require 'fx'\nRSpec.describe Fx do\n  it('adds') { expect(Fx.add(1, 2)).to eq(3) }\nend\n",
        "spec/heartgold_spec_spec.rb": "require 'fx'\nRSpec.describe 'heartgold spec' do\n  it('adds') { expect(Fx.add(2, 2)).to eq(5) }\nend\n",
        ".rspec": "-I lib\n",
        ".heartgold_probe.rb": "require 'json'\nrequire 'fx'\nputs [[2, 2], [0, 0]].map { |a, b| '=' + JSON.generate(Fx.add(a, b)) }.to_json\n",
    },
    "cpp": {
        "CMakeLists.txt": "cmake_minimum_required(VERSION 3.16)\nproject(fx CXX)\nenable_testing()\nadd_library(fx fx.cpp)\nadd_executable(fx_test tests/fx_test.cpp)\ntarget_link_libraries(fx_test fx)\nadd_test(NAME fx_test COMMAND fx_test)\nadd_executable(heartgold_spec_exe tests/heartgold_spec.cpp)\ntarget_link_libraries(heartgold_spec_exe fx)\nadd_test(NAME heartgold_spec COMMAND heartgold_spec_exe)\nadd_executable(heartgold_probe tests/heartgold_probe.cpp)\ntarget_link_libraries(heartgold_probe fx)\n",
        "fx.h": "int add(int a, int b);\n",
        "fx.cpp": '#include "fx.h"\nint add(int a, int b) { return a + b; }\n',
        "tests/fx_test.cpp": '#include "../fx.h"\nint main() { return add(1, 2) == 3 ? 0 : 1; }\n',
        "tests/heartgold_spec.cpp": '#include "../fx.h"\nint main() { return add(2, 2) == 5 ? 0 : 1; }\n',
        "tests/heartgold_probe.cpp": '#include "../fx.h"\n#include <stdio.h>\nint main() { printf("[\\"=%d\\",\\"=%d\\"]\\n", add(2, 2), add(0, 0)); }\n',
    },
    "php": {
        "composer.json": '{"autoload": {"files": ["src/fx.php"]}}\n',
        "src/fx.php": "<?php\nfunction fx_add(int $a, int $b): int { return $a + $b; }\n",
        "tests/FxTest.php": "<?php\nrequire_once __DIR__ . '/../src/fx.php';\nuse PHPUnit\\Framework\\TestCase;\nfinal class FxTest extends TestCase { public function testAdd(): void { $this->assertSame(3, fx_add(1, 2)); } }\n",
        "tests/HeartgoldSpecTest.php": "<?php\nrequire_once __DIR__ . '/../src/fx.php';\nuse PHPUnit\\Framework\\TestCase;\nfinal class HeartgoldSpecTest extends TestCase { public function testAdd(): void { $this->assertSame(5, fx_add(2, 2)); } }\n",
        ".heartgold_probe.php": "<?php\nrequire __DIR__ . '/src/fx.php';\necho json_encode(['=' . json_encode(fx_add(2, 2)), '=' . json_encode(fx_add(0, 0))]), \"\\n\";\n",
    },
    "dotnet": None,  # built by `dotnet new` below
}

TOOL = {"python": "python3", "js": "node", "rust": "cargo", "go": "go", "java": "mvn", "ruby": "rspec", "cpp": "cmake", "php": "phpunit", "dotnet": "dotnet"}


def sh(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=900, env=ENV)
    return p.returncode, p.stdout + p.stderr


def dotnet_fixture(root: pathlib.Path):
    sh("dotnet new xunit -o tests --name FxTests --force >/dev/null", root)
    (root / "tests" / "UnitTest1.cs").unlink(missing_ok=True)
    (root / "tests" / "Fx.cs").write_text("public static class Fx { public static int Add(int a, int b) => a + b; }\n")
    (root / "tests" / "FxTest.cs").write_text("using Xunit;\npublic class FxTest { [Fact] public void Add() => Assert.Equal(3, Fx.Add(1, 2)); }\n")
    (root / "tests" / "HeartgoldSpecTests.cs").write_text("using Xunit;\npublic class HeartgoldSpecTests { [Fact] public void Add() => Assert.Equal(5, Fx.Add(2, 2)); }\n")
    sh("dotnet new sln -n fx --force >/dev/null && dotnet sln add tests/FxTests.csproj >/dev/null", root)


@pytest.mark.parametrize("name", sorted(TOOL))
def test_adapter_on_a_real_project(name, tmp_path):
    if not shutil.which(TOOL[name], path=ENV["PATH"]):
        pytest.skip(f"{TOOL[name]} is not installed")
    root = tmp_path / name
    root.mkdir()
    if F[name] is None:
        dotnet_fixture(root)
    else:
        for rel, text in F[name].items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
    lang = detect(root)
    assert lang.name == name
    own = [r for r in (str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()) if lang.is_test_file(r) and "heartgold" not in r.lower()]
    code, out = sh(lang.run_orig(own), root)
    passed, failed, _ = parse_results(out)
    assert code == 0 and failed == 0 and passed >= 1, f"own tests:\n{out[-2500:]}"
    code, out = sh(lang.run_kind("spec"), root)
    passed, failed, _ = parse_results(out)
    assert code != 0 and failed >= 1 and passed == 0, f"heartgold spec test must run alone and fail:\n{out[-2500:]}"
    if lang.probe_cmd:
        # the probe's answer is on stdout; toolchains print warnings on stderr
        p = subprocess.run(lang.probe_cmd, cwd=root, shell=True, capture_output=True, text=True, timeout=900, env=ENV)
        assert json.loads(p.stdout.strip().splitlines()[-1]) == ["=4", "=0"], (p.stdout + p.stderr)[-1500:]
