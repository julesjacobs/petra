#!/usr/bin/env bash
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
export PATH="${HOME}/.ghcup/bin:${PATH}"
command -v ghc >/dev/null
command -v cabal >/dev/null
checkout() {
    local repo="$1" revision="$2" directory="$3"
    if [[ ! -d "$directory/.git" ]]; then
        git clone "https://github.com/dixonary/$repo" "$directory"
        git -C "$directory" checkout "$revision"
    fi
    [[ "$(git -C "$directory" rev-parse HEAD)" == "$revision" ]] || {
        echo "Unexpected revision in $directory; refusing to replace it." >&2
        exit 1
    }
}
checkout kosaraju 48b41f249bc0f93707402b2c11b21024f041a286 "$project_dir/vendor/KReach"
cd "$project_dir/vendor/KReach"
checkout vass 21020e8246353f14042c4e8070a6af093e2aebf2 deps/vass
checkout duvet 1cb22f34ed52ed5f8ca6ce639696cdc7c4c4e1f0 deps/duvet
checkout karp-miller cf24259b56dc36f30ab8f4f6e19a31709cbf1038 deps/karp-miller
python3 - <<'PY'
from pathlib import Path
for name in ['vass', 'duvet', 'karp-miller']:
    p = Path('deps') / name
    text = (p / 'package.yaml').read_text()
    version = next(line.split(':', 1)[1].strip() for line in text.splitlines() if line.startswith('version:'))
    def items(key):
        out = []
        for line in text.split(key + ':', 1)[1].splitlines()[1:]:
            if line.startswith('- '):
                out.append(line[2:])
            elif line and not line.startswith('#'):
                break
        return out
    deps = [d for d in items('dependencies')
            if not (d.startswith('diagrams') or d in ['SVGFonts', 'force-layout'])]
    modules = ['.'.join(f.relative_to(p / 'src').with_suffix('').parts)
               for f in sorted((p / 'src').rglob('*.hs')) if f.name != 'Render.hs']
    (p / (name + '.cabal')).write_text(
        'cabal-version: 2.4\nname: ' + name + '\nversion: ' + version + '\nbuild-type: Simple\n'
        'library\n  hs-source-dirs: src\n  exposed-modules: ' + ', '.join(modules) +
        '\n  build-depends: ' + ', '.join(deps) +
        '\n  default-extensions: ' + ', '.join(items('default-extensions')) +
        '\n  default-language: Haskell2010\n')
Path('cabal.project').write_text(
    'packages: . deps/vass deps/duvet deps/karp-miller\noptimization: 2\n'
    'index-state: 2026-08-11T20:49:38Z\n')
PY
cat > compatibility.patch <<'PATCH'
diff --git a/app/Main.hs b/app/Main.hs
index 2d09c95..023b63e 100644
--- a/app/Main.hs
+++ b/app/Main.hs
@@ -15,13 +15,21 @@ import Data.VASS.Reachability.Kosaraju
 import Options.Applicative
 
 import System.IO.Silently
+import qualified Data.Map as Map
+import qualified Data.Set as Set
+import qualified Data.Vector as Vector
+import Data.String (fromString)
+import Text.Read (readMaybe)
+import System.FilePath (takeExtension)
+import System.Exit (die)
+import Data.VASS
 
 
 main :: IO ()
 main = do
     KReachOptions{..} <- execParser $ optParser `info` mempty
 
-    problem <- readAny file
+    problem <- if takeExtension file == ".kvass" then readPointVASS file else readAny file
 
     let withVerbosity = if quiet then silence else id
         runMode :: IO String
@@ -66,4 +74,33 @@ optParser = KReachOptions
             <|>
             pure KReach 
         )
-    <*> strArgument (metavar "FILENAME" <> help "The file to run the checker on.")
\ No newline at end of file
+    <*> strArgument (metavar "FILENAME" <> help "The file to run the checker on.")
+
+-- Pure-effect VASS input avoids encoding finite control states as counters.
+readPointVASS :: FilePath -> IO CovProblem
+readPointVASS path = do
+    contents <- readFile path
+    case readMaybe contents :: Maybe (Integer, [Integer], Integer, [Integer], [(Integer, Integer, [Integer])]) of
+        Nothing -> die "Invalid .kvass tuple"
+        Just (start, initialCounts, finish, finalCounts, edges)
+            | length initialCounts /= length finalCounts
+              || any (< 0) (initialCounts ++ finalCounts)
+              || any (\(_, _, ds) -> length ds /= length initialCounts) edges
+                -> die "Invalid .kvass dimensions or endpoint counters"
+            | otherwise -> do
+                let stateName = fromString . ("q" ++) . show
+                    n = length initialCounts
+                    initial = Configuration (stateName start) (Vector.fromList initialCounts)
+                    target = Configuration (stateName finish) (Vector.fromList finalCounts)
+                    states = Set.fromList $ map stateName (start : finish : concatMap (\(a,b,_) -> [a,b]) edges)
+                    transitions = Map.fromListWith (<>)
+                        [ (stateName a, Vector.singleton $ Transition
+                            (fromString $ "t" ++ show i)
+                            (Vector.fromList $ map (max 0 . negate) ds)
+                            (Vector.fromList $ map (max 0) ds)
+                            (stateName b))
+                        | (i, (a,b,ds)) <- zip [(0::Integer)..] edges ]
+                    system = VASS (fromIntegral n)
+                        (Vector.fromList [fromString $ "p" ++ show i | i <- [0..n-1]])
+                        states transitions
+                return $ CovProblem {..}
diff --git a/kosaraju.cabal b/kosaraju.cabal
index 841f195..ec03763 100644
--- a/kosaraju.cabal
+++ b/kosaraju.cabal
@@ -46,7 +46,7 @@ library
     , mtl
     , optparse-applicative
     , pretty-simple
-    , sbv ==8.5
+    , sbv ==14.5
     , silently
     , text
     , unamb
@@ -74,7 +74,7 @@ executable kosaraju
     , mtl
     , optparse-applicative
     , pretty-simple
-    , sbv ==8.5
+    , sbv ==14.5
     , silently
     , text
     , unamb
@@ -104,7 +104,7 @@ test-suite kosaraju-test
     , mtl
     , optparse-applicative
     , pretty-simple
-    , sbv ==8.5
+    , sbv ==14.5
     , silently
     , text
     , unamb
diff --git a/src/Data/VASS/Reachability/Kosaraju.hs b/src/Data/VASS/Reachability/Kosaraju.hs
index a00a50f..2731b04 100644
--- a/src/Data/VASS/Reachability/Kosaraju.hs
+++ b/src/Data/VASS/Reachability/Kosaraju.hs
@@ -6,7 +6,7 @@ the Reachability decision problem over Vector Addition Systems with States.
 
 module Data.VASS.Reachability.Kosaraju where
 
-import Data.SBV
+import Data.SBV hiding (project)
 import Documentation.SBV.Examples.Existentials.Diophantine (Solution(..))
 
 import Data.List ((\\), elemIndex, find, transpose, concat, concatMap, nub)
diff --git a/src/LDN.hs b/src/LDN.hs
index fcab1c4..89bf720 100644
--- a/src/LDN.hs
+++ b/src/LDN.hs
@@ -1,4 +1,4 @@
-{-# LANGUAGE FlexibleContexts #-}
+{-# LANGUAGE FlexibleContexts, ScopedTypeVariables, DataKinds #-}
 
 {-| This is an implementation of a linear diophantine equation solver by Levent Erkok.
 
@@ -15,7 +15,9 @@ import Data.Function (on)
 
 import Data.Char(toLower)
 
-import System.Environment.Blank
+import System.Environment (lookupEnv)
+import GHC.TypeNats (SomeNat(..), someNatVal)
+import Data.Proxy (Proxy)
 
 --------------------------------------------------------------------------------------------------
 -- * Solving diophantine equations
@@ -41,15 +43,14 @@ ldn problem = do
 basis :: [[SInteger]] -> IO [[Integer]]
 basis m = do
     solver <- chooseSolver
-    extractModels <$> allSatWith solver cond
-    where 
-        cond = do 
-            as <- mkExistVars  n
-            bs <- mkForallVars n
-
+    case someNatVal (fromIntegral n) of
+        SomeNat (_ :: Proxy arity) -> extractModels <$> allSatWith solver (do
+            as <- mkFreeVars n
             setLogic AUFLIA
-
-            return $ ok as .&&  (ok bs .=> as .== bs .|| sNot (bs `less` as))
+            constrain $ \(ForallN bs :: ForallN arity "bs" Integer) ->
+                ok as .&& (ok bs .=> as .== bs .|| sNot (bs `less` as))
+            return sTrue)
+    where
         n = if null m then 0 else length (head m)
         ok xs = sAny (.> 0) xs .&& sAll (.>= 0) xs .&& sAnd [sum (zipWith (*) r xs) .== 0 | r <- m]
         as `less` bs = sAnd (zipWith (.<=) as bs) .&& sOr (zipWith (.<) as bs)
@@ -62,7 +63,7 @@ deriving instance Eq Solver
 chooseSolver :: IO SMTConfig
 chooseSolver = do
 
-    solverEnvironmentVar <- getEnv "KOSARAJU_SOLVER"
+    solverEnvironmentVar <- lookupEnv "KOSARAJU_SOLVER"
     case fmap toLower <$> solverEnvironmentVar of
         Just "z3" -> return z3
         Just "cvc4" -> return cvc4
@@ -70,7 +71,7 @@ chooseSolver = do
 
 findSolver :: IO SMTConfig
 findSolver = do
-    availableSolvers <- sbvAvailableSolvers
+    availableSolvers <- getAvailableSolvers
 
     let usableSolvers = availableSolvers `intersect` [z3, cvc4]
         firstSolver   = listToMaybe usableSolvers
PATCH
if git apply --reverse --check compatibility.patch 2>/dev/null; then
    : # Already applied.
else
    git apply --check compatibility.patch
    git apply compatibility.patch
fi
cp "$project_dir/scripts/kreach.cabal.project.freeze" cabal.project.freeze
cabal build exe:kosaraju -j4
mkdir -p bin
cp "$(cabal list-bin exe:kosaraju)" bin/kosaraju
cabal freeze
printf 'KReach executable: %s/vendor/KReach/bin/kosaraju\n' "$project_dir"
